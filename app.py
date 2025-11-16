import streamlit as st
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
from pathlib import Path
import base64
import sqlite3
import hashlib
import os
import json

# --- PDF amélioré avec en-tête/pied-de-page et éléments graphiques ---
class CustomPDF(FPDF):
    def __init__(self, teacher_name: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maitre = teacher_name
        self.first_page = True
        self.images_dir = Path(__file__).parent / "images"
        # Try to resolve emoji images for Likert scale
        self.emoji_paths = {
            0: self._first_existing(["emoji_graine.png", "graine.png", "seed.png"]),
            1: self._first_existing(["emoji_pousse.png", "pousse.png", "sprout.png"]),
            2: self._first_existing(["emoji_fleur.png", "fleur.png", "flower.png"]),
        }

    def rounded_rect(self, x, y, w, h, r=5, style='DF'):
        k = self.k
        hp = self.h
        if style == 'F':
            op = 'f'
        elif style in ['FD', 'DF']:
            op = 'B'
        else:
            op = 'S'
        my_arc = 4/3*(2**0.5 - 1)
        # start top-left corner
        self._out("%.2f %.2f m" % ((x + r) * k, (hp - y) * k))
        # top edge
        self._out("%.2f %.2f l" % ((x + w - r) * k, (hp - y) * k))
        # top-right corner arc
        self._Arc(x + w - r + my_arc * r, y, x + w, y + r - my_arc * r, x + w, y + r)
        # right edge
        self._out("%.2f %.2f l" % (((x + w) * k), (hp - (y + h - r)) * k))
        # bottom-right corner arc
        self._Arc(x + w, y + h - r + my_arc * r, x + w - r + my_arc * r, y + h, x + w - r, y + h)
        # bottom edge
        self._out("%.2f %.2f l" % (((x + r) * k), (hp - (y + h)) * k))
        # bottom-left corner arc
        self._Arc(x + r - my_arc * r, y + h, x, y + h - r + my_arc * r, x, y + h - r)
        # left edge
        self._out("%.2f %.2f l" % (x * k, (hp - (y + r)) * k))
        # top-left corner arc
        self._Arc(x, y + r - my_arc * r, x + r - my_arc * r, y, x + r, y)
        self._out(op)

    def _Arc(self, x1, y1, x2, y2, x3, y3):
        h = self.h
        self._out(
            "%.2f %.2f %.2f %.2f %.2f %.2f c" % (
                x1 * self.k,
                (h - y1) * self.k,
                x2 * self.k,
                (h - y2) * self.k,
                x3 * self.k,
                (h - y3) * self.k,
            )
        )

    def rounded_top_rect(self, x, y, w, h, r=5, style='F'):
        # Draw a rectangle with rounded top corners only, straight bottom
        k = self.k
        hp = self.h
        if style == 'F':
            op = 'f'
        elif style in ['FD', 'DF']:
            op = 'B'
        else:
            op = 'S'
        my_arc = 4/3*(2**0.5 - 1)
        # start at top-left inner corner
        self._out("%.2f %.2f m" % ((x + r) * k, (hp - y) * k))
        # top edge
        self._out("%.2f %.2f l" % ((x + w - r) * k, (hp - y) * k))
        # top-right arc
        self._Arc(x + w - r + my_arc * r, y, x + w, y + r - my_arc * r, x + w, y + r)
        # right edge down to bottom
        self._out("%.2f %.2f l" % (((x + w) * k), (hp - (y + h)) * k))
        # bottom edge straight to left
        self._out("%.2f %.2f l" % ((x * k), (hp - (y + h)) * k))
        # left edge up to top-left arc start
        self._out("%.2f %.2f l" % (x * k, (hp - (y + r)) * k))
        # top-left arc
        self._Arc(x, y + r - my_arc * r, x + r - my_arc * r, y, x + r, y)
        self._out(op)

    def _first_existing(self, candidates):
        for name in candidates:
            p = self.images_dir / name
            if p.exists():
                return p
        return None

    def draw_likert_scale(self, selected_index: int, x: float, y: float, box_w: float = 14, box_h: float = 12, gap: float = 6):
        # Draw three boxes horizontally and highlight selected
        for i in range(3):
            bx = x + i * (box_w + gap)
            # border color
            if i == selected_index:
                self.set_draw_color(0, 173, 239)
                self.set_line_width(0.6)
            else:
                self.set_draw_color(180, 180, 180)
                self.set_line_width(0.2)
            self.rounded_rect(bx, y, box_w, box_h, r=2, style='D')
            # place emoji image if available
            img_path = self.emoji_paths.get(i)
            # if specific image missing, fall back to any available image to avoid numbers
            if img_path is None:
                for alt in self.emoji_paths.values():
                    if alt is not None:
                        img_path = alt
                        break
            if img_path is not None:
                try:
                    self.image(str(img_path), x=bx + 2, y=y + 2, w=box_w - 4, h=box_h - 4)
                except Exception:
                    pass
            else:
                # fallback: ASCII marker (avoid Unicode)
                self.set_xy(bx, y + 3)
                labels = ["1", "2", "3"]
                self.cell(box_w, 6, labels[i], align="C")

    def calculate_multicell_height(self, text: str, width: float, line_height: float) -> float:
        # Approximate height of a multicell for current font settings
        total_lines = 0
        for paragraph in str(text).split("\n"):
            if not paragraph:
                total_lines += 1
                continue
            current_line = ""
            for word in paragraph.split(" "):
                test = (current_line + (" " if current_line else "") + word).strip()
                if self.get_string_width(test) <= width:
                    current_line = test
                else:
                    total_lines += 1
                    current_line = word
            if current_line:
                total_lines += 1
        return max(line_height, total_lines * line_height)

    def header(self):
        if not self.first_page:
            return
        # Logos et visuels si disponibles
        logo = self.images_dir / "logo_geneve2.png"
        garcon = self.images_dir / "eleve_garcon.png"
        fille = self.images_dir / "eleve_fille.png"
        if logo.exists():
            self.image(str(logo), x=10, y=3, w=15)
        if garcon.exists():
            self.image(str(garcon), x=45, y=7.3, w=20)
        if fille.exists():
            self.image(str(fille), x=135, y=6.3, w=20)

        # Titre centré
        self.set_font("Arial", "B", 20)
        self.set_xy(0, 10)
        self.cell(0, 10, "Observation de séance", align="C")
           
        # Bannière
        x_rect, y_rect, w_rect, h_rect, radius = 10, 30, 190, 15, 5
        self.set_fill_color(0, 173, 239)
        self.set_draw_color(0, 173, 239)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 16)
        self.rounded_rect(x_rect, y_rect, w_rect, h_rect, r=radius, style='DF')
        self.set_xy(x_rect, y_rect + 3)
        # Remplacer le texte de bannière par la date du jour
        self.cell(w_rect, h_rect - 6, datetime.now().strftime("%d/%m/%Y"), 0, 0, "C")

        # Reset couleur texte et marquer fin de première page
        self.set_text_color(0, 0, 0)
        self.ln(20)
        self.first_page = False

    def footer(self):
        # Positionnement depuis le bas
        self.set_y(-25)
        self.set_font("Arial", "", 9)
        self.cell(0, 4, "Direction générale de l'enseignement obligatoire", 0, 1, "C")
        self.cell(0, 4, "Service enseignement et évaluation", 0, 1, "C")
        # Pagination
        self.set_y(-15)
        self.set_font("Arial", "I", 9)
        self.cell(0, 10, f"{self.page_no()}/{{nb}}", 0, 0, "R")

# --- Données enrichies avec les 7 domaines, compétences transversales et processus cognitifs ---
domaines = {
    "Corps et motricité": {
        "icon": "🏃",
        "composantes": {
            "Motricité globale": {
                "Découverte, exploration de l'espace et orientation en variant les points de référence (son propre corps, d'autres personnes, d'autres objets,…)": {
                    "code_per": "MSN 11",
                    "Activités par contexte": {
                        "En classe": ["Parcours entre les tables en sautant à cloche-pied", "Jeu du flamant rose (tenir la position)"],
                        "Sur le banc": ["Sauter d'un banc à l'autre (faible hauteur)", "Équilibre sur un pied pendant 5 secondes"],
                        "Jeu à faire semblant": ["Imiter un kangourou dans la savane", "Pirate avec une jambe de bois"],
                        "Dehors": ["Sauter dans les cerceaux au sol", "Course à cloche-pied dans la cour"],
                        "Autres": ["Atelier motricité en EPS", "Jeux libres avec consigne motrice"]
                    },
                    "Observables": ["Tient l'équilibre ≥ 3 sec", "Change de pied spontanément", "Ne tombe pas"],
                    "compétences_transversales": ["Persévérance", "Estime de soi", "Régulation émotionnelle"],
                    "processus_cognitifs": ["Attention soutenue", "Contrôle inhibiteur", "Planification motrice"]
                },
                "Détermination de sa position ou de celle d'un objet (devant, derrière, à côté, sur, sous, entre, à l'intérieur, à l'extérieur,…) selon différents points de repères": {
                    "code_per": "MSN 11",
                    "Activités par contexte": {
                        "En classe": ["Course entre les chaises avec arrêt au signal", "Jeu du feu vert/feu rouge"],
                        "Sur le banc": ["Marche rapide puis arrêt net", "Déplacement contrôlé"],
                        "Jeu à faire semblant": ["Livrer un message urgent au roi", "Échapper au dragon puis se figer"],
                        "Dehors": ["Relais avec départ/arrêt", "Course avec plots et arrêt sur cible"],
                        "Autres": ["Jeux sportifs collectifs", "Ateliers EPS"]
                    },
                    "Observables": ["Freine sans glisser", "S'arrête pile sur la cible", "Contrôle sa vitesse"],
                    "compétences_transversales": ["Contrôle de soi", "Respect des règles", "Adaptabilité"],
                    "processus_cognitifs": ["Inhibition", "Attention sélective", "Temps de réaction"]
                }
            }
        }
    },
    "Affectivité": {
        "icon": "❤️",
        "composantes": {
            "Gestion des émotions": {
                "Identifier ses émotions": {
                    "code_per": "AF 21",
                    "Activités par contexte": {
                        "En classe": ["Raconter une histoire avec des émotions", "Albums sur les émotions"],
                        "Sur le banc": ["Discussion en binôme : 'Quand j’étais triste…'", "Cartes émotions à identifier"],
                        "Jeu à faire semblant": ["Jouer une scène de dispute/réconciliation", "Théâtre d’ombres avec émotions"],
                        "Dehors": ["Expression corporelle libre : 'montre la colère'", "Jeux de rôle dans la cabane"],
                        "Autres": ["Coin calme avec miroir et pictos", "Rituels du matin (météo des émotions)"]
                    },
                    "Observables": ["Nomme l’émotion ressentie", "Utilise un vocabulaire varié", "Reconnaît l’émotion chez autrui"],
                    "compétences_transversales": ["Empathie", "Expression verbale", "Autoconscience"],
                    "processus_cognitifs": ["Mémoire sémantique", "Reconnaissance faciale", "Métacognition"]
                }
            }
        }
    },
    "Sociabilité": {
        "icon": "🤝",
        "composantes": {
            "Coopération": {
                "Travailler en groupe": {
                    "code_per": "SO 31",
                    "Activités par contexte": {
                        "En classe": ["Construire une tour en équipe", "Jeu de rôle collectif"],
                        "Sur le banc": ["Partager un matériel à tour de rôle", "Discuter d’une solution commune"],
                        "Jeu à faire semblant": ["Créer une histoire à plusieurs", "Jouer une famille ou une équipe"],
                        "Dehors": ["Jeu de ballon coopératif", "Parcours en binôme"],
                        "Autres": ["Projets interclasses", "Ateliers collaboratifs"]
                    },
                    "Observables": ["Attend son tour", "Propose des idées", "Aide un camarade"],
                    "compétences_transversales": ["Collaboration", "Communication", "Responsabilité"],
                    "processus_cognitifs": ["Théorie de l’esprit", "Flexibilité cognitive", "Mémoire de travail"]
                }
            }
        }
    },
    "Littératie": {
        "icon": "📖",
        "composantes": {
            "Compréhension orale": {
                "Suivre une consigne complexe": {
                    "code_per": "LI 41",
                    "Activités par contexte": {
                        "En classe": ["Jeu des consignes à 2 étapes", "Écoute d’histoires avec questions"],
                        "Sur le banc": ["Répéter une consigne en ses mots", "Jeu de 'Simon dit'"],
                        "Jeu à faire semblant": ["Suivre les règles d’un jeu inventé", "Jouer un rôle avec instructions"],
                        "Dehors": ["Chasse au trésor avec indices verbaux", "Jeu de piste oral"],
                        "Autres": ["Temps d’écoute active", "Rituels narratifs"]
                    },
                    "Observables": ["Exécute les étapes dans l’ordre", "Demande des clarifications", "Résume la consigne"],
                    "compétences_transversales": ["Écoute active", "Clarté d’expression", "Autonomie"],
                    "processus_cognitifs": ["Mémoire de travail", "Compréhension syntaxique", "Attention auditive"]
                }
            }
        }
    },
    "Numératie": {
        "icon": "🔢",
        "composantes": {
            "Dénombrement": {
                "Compter jusqu'à 10 avec correspondance terme à terme": {
                    "code_per": "NU 51",
                    "Activités par contexte": {
                        "En classe": ["Compter les crayons", "Jeu de la marchande"],
                        "Sur le banc": ["Compter des jetons", "Associer chiffre et quantité"],
                        "Jeu à faire semblant": ["Préparer 5 assiettes pour les invités", "Donner 3 pièces d’or au pirate"],
                        "Dehors": ["Compter les sauts", "Ramasser 7 feuilles"],
                        "Autres": ["Manipulations avec réglettes", "Jeux de société numériques"]
                    },
                    "Observables": ["Pointe chaque objet une fois", "Dit la suite numérique sans sauter", "Arrête au bon nombre"],
                    "compétences_transversales": ["Précision", "Logique", "Persévérance"],
                    "processus_cognitifs": ["Attention sélective", "Mémoire de travail", "Inhibition"]
                }
            }
        }
    },
    "Éveil à l'environnement": {
        "icon": "🌍",
        "composantes": {
            "Découverte du vivant": {
                "Observer les plantes et les animaux": {
                    "code_per": "EV 61",
                    "Activités par contexte": {
                        "En classe": ["Coin nature avec loupe", "Album photo de la cour"],
                        "Sur le banc": ["Dessiner une feuille observée", "Classer des images animaux/plantes"],
                        "Jeu à faire semblant": ["Jardinier ou vétérinaire", "Explorateur de la jungle"],
                        "Dehors": ["Balade sensorielle", "Création d’un herbier"],
                        "Autres": ["Visite d’un jardin", "Expériences de germination"]
                    },
                    "Observables": ["Nomme ce qu’il voit", "Pose des questions", "Compare deux éléments"],
                    "compétences_transversales": ["Curiosité", "Observation", "Respect de la nature"],
                    "processus_cognitifs": ["Perception visuelle", "Catégorisation", "Mémoire épisodique"]
                }
            }
        }
    }
}

# --- Initialisation de session_state ---
if "observations" not in st.session_state:
    st.session_state.observations = []
if "show_sidebar" not in st.session_state:
    st.session_state.show_sidebar = False
if "reset_requested" not in st.session_state:
    st.session_state.reset_requested = False

# --- Base de données: enseignants et élèves ---
DB_PATH = Path(__file__).parent / "app_data.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(teacher_id, name),
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NULL,
                domaine TEXT,
                composante TEXT,
                apprentissage TEXT,
                mode TEXT,
                observables_json TEXT,
                commentaire TEXT,
                activites_json TEXT,
                competences_mobilisees_json TEXT,
                processus_mobilises_json TEXT,
                competence_mise_en_avant TEXT,
                processus_mis_en_avant TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
            );
        """)
        conn.commit()

def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    if not salt_hex:
        salt = os.urandom(16)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)
    h = hashlib.sha256()
    h.update(salt + password.encode("utf-8"))
    return h.hexdigest(), salt_hex

def create_teacher(name: str, email: str, password: str) -> tuple[bool, str | None, dict | None]:
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = (password or "").strip()
    if not name or not email or not password:
        return False, "Veuillez renseigner nom, email et mot de passe.", None
    pwd_hash, salt_hex = _hash_password(password)
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO teachers (name, email, password_hash, salt) VALUES (?, ?, ?, ?)",
                (name, email, pwd_hash, salt_hex),
            )
            teacher_id = cur.lastrowid
            conn.commit()
            return True, None, {"id": teacher_id, "name": name, "email": email}
    except sqlite3.IntegrityError:
        return False, "Cet email est déjà utilisé.", None
    except Exception as e:
        return False, f"Erreur: {e}", None

def authenticate_teacher(email: str, password: str) -> tuple[bool, str | None, dict | None]:
    email = (email or "").strip().lower()
    password = (password or "").strip()
    if not email or not password:
        return False, "Email et mot de passe requis.", None
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, password_hash, salt FROM teachers WHERE email = ?", (email,))
        row = cur.fetchone()
        if not row:
            return False, "Identifiants incorrects.", None
        teacher_id, name, email_db, pwd_hash_db, salt_hex = row
        calc_hash, _ = _hash_password(password, salt_hex)
        if calc_hash != pwd_hash_db:
            return False, "Identifiants incorrects.", None
        return True, None, {"id": teacher_id, "name": name, "email": email_db}

def list_students_db(teacher_id: int) -> list[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM students WHERE teacher_id = ? ORDER BY name COLLATE NOCASE", (teacher_id,))
        return [{"id": r[0], "name": r[1]} for r in cur.fetchall()]

def add_student_db(teacher_id: int, name: str) -> tuple[bool, str | None]:
    name = (name or "").strip()
    if not name:
        return False, "Nom d'élève requis."
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("INSERT OR IGNORE INTO students (teacher_id, name) VALUES (?, ?)", (teacher_id, name))
            conn.commit()
        return True, None
    except Exception as e:
        return False, f"Erreur lors de l'ajout: {e}"

def delete_student_db(teacher_id: int, student_id: int) -> tuple[bool, str | None]:
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM students WHERE id = ? AND teacher_id = ?", (student_id, teacher_id))
            conn.commit()
        return True, None
    except Exception as e:
        return False, f"Suppression impossible: {e}"

def delete_observation_db(obs_id: int, teacher_id: int | None) -> tuple[bool, str | None]:
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            if teacher_id is None:
                cur.execute(
                    "DELETE FROM observations WHERE id = ? AND teacher_id IS NULL",
                    (obs_id,)
                )
            else:
                cur.execute(
                    "DELETE FROM observations WHERE id = ? AND teacher_id = ?",
                    (obs_id, teacher_id)
                )
            if cur.rowcount == 0:
                return False, "Aucune observation correspondante à supprimer."
            conn.commit()
            return True, None
    except Exception as e:
        return False, f"Suppression observation impossible: {e}"

def save_observation_db(obs: dict, teacher_id: int | None) -> tuple[bool, str | None, int | None]:
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO observations (
                    teacher_id, domaine, composante, apprentissage, mode,
                    observables_json, commentaire, activites_json,
                    competences_mobilisees_json, processus_mobilises_json,
                    competence_mise_en_avant, processus_mis_en_avant
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    teacher_id,
                    obs.get("Domaine"),
                    obs.get("Composante"),
                    obs.get("Apprentissage"),
                    obs.get("Mode"),
                    json.dumps(obs.get("Observables") or [], ensure_ascii=False),
                    obs.get("Commentaire") or "",
                    json.dumps(obs.get("Activités") or [], ensure_ascii=False),
                    json.dumps(obs.get("Compétences_mobilisées") or [], ensure_ascii=False),
                    json.dumps(obs.get("Processus_mobilisés") or [], ensure_ascii=False),
                    obs.get("Compétence_mise_en_avant") or "",
                    obs.get("Processus_mis_en_avant") or "",
                ),
            )
            obs_id = cur.lastrowid
            conn.commit()
            return True, None, obs_id
    except Exception as e:
        return False, f"Erreur enregistrement observation: {e}", None

# Créer la base au démarrage
init_db()

# Session: enseignant et liste d'élèves
if "teacher" not in st.session_state:
    st.session_state.teacher = None
if "students" not in st.session_state:
    st.session_state.students = []

# Rafraîchir la liste d'élèves si connecté
if st.session_state.teacher:
    try:
        st.session_state.students = list_students_db(st.session_state.teacher["id"])
    except Exception:
        st.session_state.students = []

# --- Gestion suppression via paramètres d'URL (trash dans sidebar) ---
def _handle_delete_from_query_params():
    try:
        params = dict(st.query_params) if hasattr(st, "query_params") else st.experimental_get_query_params()
    except Exception:
        params = {}
    del_id = None
    del_idx = None
    del_student_id = None
    try:
        if params:
            if "del_obs" in params:
                val = params.get("del_obs")
                if isinstance(val, list):
                    val = val[0] if val else None
                if val is not None:
                    del_id = int(val)
            if "del_idx" in params:
                val = params.get("del_idx")
                if isinstance(val, list):
                    val = val[0] if val else None
                if val is not None:
                    del_idx = int(val)
            if "del_student" in params:
                val = params.get("del_student")
                if isinstance(val, list):
                    val = val[0] if val else None
                if val is not None:
                    del_student_id = int(val)
    except Exception:
        pass
    changed = False
    if del_id is not None:
        current_teacher_id = st.session_state.teacher["id"] if st.session_state.get("teacher") else None
        ok_del, _err_del = delete_observation_db(del_id, current_teacher_id)
        # Retirer de la session si présent
        for j, o in enumerate(list(st.session_state.observations)):
            if o.get("db_id") == del_id:
                try:
                    st.session_state.observations.pop(j)
                except Exception:
                    pass
                break
        changed = True
    elif del_idx is not None:
        # Suppression par index de session (fallback)
        try:
            if 0 <= del_idx < len(st.session_state.observations):
                st.session_state.observations.pop(del_idx)
                changed = True
        except Exception:
            pass
    if del_student_id is not None and st.session_state.get("teacher"):
        try:
            ok_stu, _err_stu = delete_student_db(st.session_state.teacher["id"], del_student_id)
            if ok_stu:
                st.session_state.students = list_students_db(st.session_state.teacher["id"])
                changed = True
        except Exception:
            pass
    if changed:
        # Nettoyer les paramètres
        try:
            if hasattr(st, "query_params"):
                # Clear only our keys
                qp = dict(st.query_params)
                qp.pop("del_obs", None)
                qp.pop("del_idx", None)
                qp.pop("del_student", None)
                st.experimental_set_query_params(**{k: v for k, v in qp.items()})
            else:
                st.experimental_set_query_params()
        except Exception:
            pass
        try:
            st.rerun()
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass

_handle_delete_from_query_params()

# --- Fonction pour réinitialiser tous les checkboxes ---
def reset_all_checkboxes():
    keys_to_reset = [k for k in st.session_state.keys() if k.startswith(("classe_", "eleve_", "comment_"))]
    for k in keys_to_reset:
        del st.session_state[k]
    st.session_state.reset_requested = True

# --- Callback: ajouter un élève dans une liste dédiée et vider le champ ---
def add_student_to_list(list_key: str, input_key: str):
    name = st.session_state.get(input_key, "").strip()
    if name:
        current_list = st.session_state.get(list_key, [])
        if name not in current_list:
            current_list.append(name)
            st.session_state[list_key] = current_list
        st.session_state[input_key] = ""

# --- Helper: encoder image en base64 ---
def img_to_base64(img_path: Path) -> str:
    try:
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""

# --- CSS pour le bouton et les expanders ---
st.markdown("""
<style>
/* Bouton stylisé */
.big-color-button {
    background-color: #1f77b4;  /* couleur personnalisée */
    color: white !important;
    padding: 20px 40px !important;
    font-size: 24px !important;
    border: none !important;
    border-radius: 10px !important;
    cursor: pointer;
    display: inline-block;
    margin: 20px 0;
    text-align: center;
    width: 100%;
}
.big-color-button:hover {
    background-color: #155a8a !important;
}

/* Supprimer les bordures des expanders */
[data-testid="stExpander"] details {
    border: none !important;
    box-shadow: none !important;
    background-color: transparent !important;
}
[data-testid="stExpander"] summary {
    border: none !important;
    box-shadow: none !important;
    background-color: #f8f9fa !important;  /* facultatif : fond clair */
    padding: 8px 0 !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)

# --- Styles des onglets : plus grands et 50% de largeur chacun ---
st.markdown(
    """
    <style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        flex: 1 1 50%;
        max-width: 50%;
    }
    /* Agrandir et harmoniser la police des libellés d'onglets */
    .stTabs [data-baseweb="tab"],
    .stTabs [data-baseweb="tab"] > div,
    .stTabs [data-baseweb="tab"] > div > div {
        font-family: inherit !important;
        font-size: 1.2rem !important;
        line-height: 1.2 !important;
        font-weight: 1000 !important;
    }
    .stTabs [data-baseweb="tab"] > div {
        padding: 12px 0;
        justify-content: center;
        min-height: 56px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Style spécifique: onglets des lieux (ctx-tabs-marker)
st.markdown(
    """
    <style>
    .ctx-tabs-marker + div.stTabs [data-baseweb="tab"],
    .ctx-tabs-marker + div.stTabs [data-baseweb="tab"] > div,
    .ctx-tabs-marker + div.stTabs [data-baseweb="tab"] > div > div {
        font-size: 0.5rem !important; /* légèrement plus petit */
        font-weight: 700 !important;
    }
    .ctx-tabs-marker + div.stTabs [data-baseweb="tab"] > div {
        padding: 4px 0;
        min-height: 30px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Largeur de la sidebar ---
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        min-width: 380px !important;
        max-width: 380px !important;
    }
    [data-testid="stSidebar"] > div {
        min-width: 380px !important;
        max-width: 380px !important;
    }
    /* Style des icônes poubelles (petites et rouges) */
    .trash-btn {
        color: #cc0000 !important;
        font-size: 0.9rem !important;
        text-decoration: none !important;
        display: inline-block;
        padding: 2px 6px;
        border-radius: 4px;
        border: 1px solid transparent;
        line-height: 1;
    }
    .trash-btn:hover {
        color: #a00000 !important;
        background-color: rgba(204,0,0,0.08);
        border-color: rgba(204,0,0,0.15);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Interface principale ---
st.set_page_config(page_title="Enseigner et Évaluer en 1P-2P", layout="wide")

# Header avec date
col1, col2 = st.columns([3, 1])
with col1:
    st.title("Enseigner et Évaluer en 1P-2P")
with col2:
    st.markdown(f"<div style='text-align: right; padding-top: 20px; font-size: 1.1rem; color: #666;'>{datetime.now().strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)

# --- Formulaire d’observation dynamique ---
for domaine, data in domaines.items():
    icon = data["icon"]
    with st.expander(f"{icon} **{domaine}**", expanded=False):
        for comp_name, criteres in data["composantes"].items():
            with st.expander(f"🟢 **Composante : {comp_name}**", expanded=False):
                for crit_name, detail in criteres.items():
                    # Critère avec indication du code PER
                    code_per = detail.get("code_per", "")
                    crit_col, code_col = st.columns([20, 1])
                    with crit_col:
                        crit_expander = st.expander(f"🔹 **Apprentissage : {crit_name}**", expanded=False)
                    with code_col:
                        if code_per:
                            st.markdown(f'<span style="color:red; font-weight:bold; font-size:1rem;">{code_per}</span>', unsafe_allow_html=True)
                    
                    with crit_expander:
                        # Section déplacée dans l'onglet Enseigner

                        tab_enseigner, tab_evaluer = st.tabs(["🧑‍🏫 Enseigner", "👀 Évaluer"])

                        with tab_enseigner:

                            st.markdown("#### 🎯 Activités pédagogiques mobilisant cet apprentissage")
                            # Espace visuel avant les onglets de lieux
                            contextes = ["En classe", "Sur le banc", "Jeu à faire semblant", "Dehors", "Autres"]
                            icones_contextes = {
                                "En classe": "🏫",
                                "Sur le banc": "🪑",
                                "Jeu à faire semblant": "🧸",
                                "Dehors": "🌳",
                                "Autres": "💡"
                            }
                            contextes_disponibles = [c for c in contextes if c in detail.get("Activités par contexte", {})]
                            if contextes_disponibles:
                                # Marqueur pour cibler uniquement ces onglets via CSS
                                st.markdown("<div class='ctx-tabs-marker'></div>", unsafe_allow_html=True)
                                tabs_ctx = st.tabs([f"{icones_contextes.get(c, '•')} {c}" for c in contextes_disponibles])
                                # Mapping activités vers MER (à compléter selon vos liens réels)
                                liens_mer = {
                                    "Parcours entre les tables en sautant à cloche-pied": "https://www.plandetudes.ch/mer",
                                    "Jeu du flamant rose (tenir la position)": "https://www.plandetudes.ch/mer",
                                    "Course entre les chaises avec arrêt au signal": "https://www.plandetudes.ch/mer",
                                }
                                logo_mer_path = Path(__file__).parent / "images" / "mer.png"
                                logo_mer_b64 = img_to_base64(logo_mer_path)
                                
                                for t, c in zip(tabs_ctx, contextes_disponibles):
                                    with t:
                                        activites = detail["Activités par contexte"][c]
                                        st.markdown("Sélectionnez l'activité réalisée :")
                                        for idx, act in enumerate(activites):
                                            key_act = f"act_{domaine}_{comp_name}_{crit_name}_{c}_{idx}"
                                            # Si l'activité a un lien MER, afficher avec logo cliquable
                                            if act in liens_mer:
                                                chk_col, mer_col = st.columns([12, 1])
                                                with chk_col:
                                                    st.checkbox(act, key=key_act)
                                                with mer_col:
                                                    st.markdown(
                                                        f'<a href="{liens_mer[act]}" target="_blank"><img src="data:image/png;base64,{logo_mer_b64}" width="56" title="Voir sur le MER"/></a>',
                                                        unsafe_allow_html=True
                                                    )
                                            else:
                                                st.checkbox(act, key=key_act)
                                        autre_key = f"autre_act_{domaine}_{comp_name}_{crit_name}_{c}"
                                        st.text_input("Autre activité (facultatif)", key=autre_key)

                            # Sélection séparée des compétences transversales et des processus cognitifs
                            comp_opts = detail["compétences_transversales"]
                            proc_opts = detail["processus_cognitifs"]
                            comp_key_mob = f"comp_mobil_{domaine}_{comp_name}_{crit_name}"
                            proc_key_mob = f"proc_mobil_{domaine}_{comp_name}_{crit_name}"

                            st.markdown("#### 🌟 Compétences transversales à mobiliser")
                            st.multiselect(
                                "Sélectionnez les compétences transversales",
                                comp_opts,
                                key=comp_key_mob,
                            )

                            st.markdown("#### 🧠 Processus cognitifs à mobiliser")
                            st.multiselect(
                                "Sélectionnez les processus cognitifs",
                                proc_opts,
                                key=proc_key_mob,
                            )

                        with tab_evaluer:
                            st.subheader("Observables")
                            observables = detail["Observables"]

                            # Affichage des curseurs d'évaluation (🌰 / 🌱 / 🌸) avec "Appliquer à"
                            scale_options = [
                                "🌰 Encore en train de germer",
                                "🌱 En train de grandir",
                                "🌸 Épanoui(e)"
                            ]
                            selected_observables = []
                            for obs in observables:
                                # En-tête + boutons d'ajout/suppression d'occurrence
                                head_col, add_col, rem_col = st.columns([10, 1, 1])
                                with head_col:
                                    st.markdown(f"**{obs}**")
                                # Compteur d'occurrences dans l'état
                                count_key = f"occ_count_{domaine}_{comp_name}_{crit_name}_{obs}"
                                if count_key not in st.session_state:
                                    st.session_state[count_key] = 1
                                with add_col:
                                    if st.button("➕", key=f"add_occ_{domaine}_{comp_name}_{crit_name}_{obs}"):
                                        st.session_state[count_key] = min(st.session_state[count_key] + 1, 10)
                                with rem_col:
                                    if st.button("➖", key=f"rem_occ_{domaine}_{comp_name}_{crit_name}_{obs}"):
                                        st.session_state[count_key] = max(1, st.session_state[count_key] - 1)

                                # Rendu des occurrences
                                for occ_idx in range(st.session_state[count_key]):
                                    st.caption(f"Occurrence {occ_idx + 1}")
                                    apply_mode = st.selectbox(
                                        "Appliquer à",
                                        ("Toute la classe", "Élèves particuliers", "Tous les élèves sauf..."),
                                        key=f"apply_{domaine}_{comp_name}_{crit_name}_{obs}_{occ_idx}"
                                    )
                                    if apply_mode == "Toute la classe":
                                        slider_col, _ = st.columns([4, 8])
                                        with slider_col:
                                            class_value = st.select_slider(
                                                "",
                                                options=scale_options,
                                                key=f"{domaine}_{comp_name}_{crit_name}_{obs}_rating_class_{occ_idx}",
                                                label_visibility="collapsed"
                                            )
                                        selected_observables.append(f"{class_value} - {obs}")
                                    elif apply_mode == "Élèves particuliers":
                                        # Saisie de plusieurs élèves séparés par des virgules et une échelle par élève
                                        names_key = f"eleves_bulk_{domaine}_{comp_name}_{crit_name}_{obs}_{occ_idx}"
                                        names_str = st.text_input(
                                            "Prénoms des élèves (séparés par des virgules)",
                                            key=names_key
                                        )
                                        names_list = [n.strip() for n in (names_str or "").split(",") if n.strip()]
                                        if names_list:
                                            st.caption(", ".join(names_list))
                                        for eleve in names_list:
                                            safe = eleve.replace(" ", "_")
                                            eleve_value = st.select_slider(
                                                eleve,
                                                options=scale_options,
                                                key=f"{domaine}_{comp_name}_{crit_name}_{obs}_rating_{safe}_{occ_idx}",
                                            )
                                            selected_observables.append(f"{eleve}: {eleve_value} - {obs}")
                                    else:
                                        # Tous les élèves sauf...
                                        excl_key = f"excl_eleves_{domaine}_{comp_name}_{crit_name}_{obs}_{occ_idx}"
                                        excl_str = st.text_input(
                                            "Prénoms des élèves exclus (séparés par des virgules)",
                                            key=excl_key
                                        )
                                        excl_list = [n.strip() for n in (excl_str or "").split(",") if n.strip()]
                                        slider_col, _ = st.columns([4, 8])
                                        with slider_col:
                                            class_except_value = st.select_slider(
                                                "",
                                                options=scale_options,
                                                key=f"{domaine}_{comp_name}_{crit_name}_{obs}_rating_class_except_{occ_idx}",
                                                label_visibility="collapsed"
                                            )
                                        if excl_list:
                                            excl_txt = ", ".join(excl_list)
                                            selected_observables.append(f"Classe (sauf {excl_txt}): {class_except_value} - {obs}")
                                        else:
                                            selected_observables.append(f"{class_except_value} - {obs}")

                            # Commentaire (placé avant la section Mise en avant)
                            comment_key = f"comment_{domaine}_{comp_name}_{crit_name}"
                            commentaire = st.text_input("Commentaire (facultatif)", key=comment_key)

                            # Mise en avant: compétences transversales et processus cognitifs
                            st.markdown("---")
                            st.markdown("### 🌟 Compétences transversales et processus cognitifs mis en avant")
                            comp_options = ["—"] + detail["compétences_transversales"]
                            proc_options = ["—"] + detail["processus_cognitifs"]
                            comp_key = f"comp_select_{domaine}_{comp_name}_{crit_name}"
                            proc_key = f"proc_select_{domaine}_{comp_name}_{crit_name}"
                            comp_selected = st.selectbox("Compétence transversale", comp_options, key=comp_key)
                            proc_selected = st.selectbox("Processus cognitif", proc_options, key=proc_key)

                            # Bouton de validation
                            if st.button("✅ Valider cette observation", key=f"valider_{domaine}_{comp_name}_{crit_name}"):
                                if selected_observables:
                                    # Récupérer activités cochées ou saisies
                                    selected_activities = []
                                    for c in contextes_disponibles:
                                        acts = detail["Activités par contexte"][c]
                                        for idx, act in enumerate(acts):
                                            if st.session_state.get(f"act_{domaine}_{comp_name}_{crit_name}_{c}_{idx}"):
                                                selected_activities.append(act)
                                        autre_val = st.session_state.get(f"autre_act_{domaine}_{comp_name}_{crit_name}_{c}", "").strip()
                                        if autre_val:
                                            selected_activities.append(autre_val)
                                    # Récupérer compétences/processus mobilisés (onglet Enseigner)
                                    comp_mobilisees = st.session_state.get(comp_key_mob, [])
                                    processus_mobilises = st.session_state.get(proc_key_mob, [])
                                    obs_entry = {
                                        "Domaine": domaine,
                                        "Composante": comp_name,
                                        "Apprentissage": crit_name,
                                        "Mode": "Selon sélection (classe/élèves)",
                                        "Observables": selected_observables.copy(),
                                        "Commentaire": commentaire or "",
                                        "Activités": selected_activities,
                                        "Compétences_mobilisées": comp_mobilisees,
                                        "Processus_mobilisés": processus_mobilises,
                                        "Compétence_mise_en_avant": (comp_selected if comp_selected != "—" else ""),
                                        "Processus_mis_en_avant": (proc_selected if proc_selected != "—" else "")
                                    }
                                    st.session_state.observations.append(obs_entry)
                                    st.success("Observation enregistrée !")
                                    # Sauvegarde en base
                                    teacher_id = st.session_state.teacher["id"] if st.session_state.get("teacher") else None
                                    ok_db, err_db, _obs_id = save_observation_db(obs_entry, teacher_id)
                                    if ok_db:
                                        # Conserver l'ID DB dans l'observation en session
                                        obs_entry["db_id"] = _obs_id
                                        try:
                                            st.session_state.observations[-1]["db_id"] = _obs_id
                                        except Exception:
                                            pass
                                        st.toast("Observation enregistrée dans la base.", icon="✅")
                                    else:
                                        st.warning(err_db or "Impossible d'enregistrer l'observation dans la base.")

# --- Sidebar dynamique ---
with st.sidebar:
        st.header("👩‍🏫 Bienvenue !")
        if not st.session_state.teacher:
            tab_login, tab_signup = st.tabs(["Se connecter", "Créer un compte"])
            with tab_login:
                email_login = st.text_input("Email", key="auth_email_login")
                pwd_login = st.text_input("Mot de passe", type="password", key="auth_pwd_login")
                if st.button("Se connecter", key="auth_login_btn"):
                    ok, err, teacher = authenticate_teacher(email_login, pwd_login)
                    if ok:
                        st.session_state.teacher = teacher
                        try:
                            st.session_state.students = list_students_db(teacher["id"])
                        except Exception:
                            st.session_state.students = []
                        st.success("Connecté.")
                        try:
                            st.rerun()
                        except Exception:
                            try:
                                st.experimental_rerun()
                            except Exception:
                                pass
                    else:
                        st.error(err or "Connexion impossible.")
            with tab_signup:
                name_new = st.text_input("Nom et prénom", key="auth_name_new")
                email_new = st.text_input("Email", key="auth_email_new")
                pwd_new = st.text_input("Mot de passe", type="password", key="auth_pwd_new")
                if st.button("Créer mon compte", key="auth_signup_btn"):
                    ok, err, teacher = create_teacher(name_new, email_new, pwd_new)
                    if ok:
                        st.session_state.teacher = teacher
                        st.session_state.students = []
                        st.success("Compte créé et connecté.")
                        try:
                            st.rerun()
                        except Exception:
                            try:
                                st.experimental_rerun()
                            except Exception:
                                pass
                    else:
                        st.error(err or "Création impossible.")
        else:
            t = st.session_state.teacher
            st.markdown(f"Connecté en tant que **{t['name']}** ({t['email']})")
            cols = st.columns([1,1])
            with cols[0]:
                if st.button("Se déconnecter", key="auth_logout_btn"):
                    st.session_state.teacher = None
                    st.session_state.students = []
                    try:
                        st.rerun()
                    except Exception:
                        try:
                            st.experimental_rerun()
                        except Exception:
                            pass
            st.markdown("### Ma classe")
            # Ajout d'un élève
            new_student = st.text_input("Ajouter un élève (Prénom Nom)", key="cls_add_one")
            if st.button("Ajouter", key="cls_add_one_btn"):
                ok, err = add_student_db(t["id"], new_student)
                if ok:
                    st.session_state.students = list_students_db(t["id"])
                    st.success("Élève ajouté.")
                else:
                    st.error(err or "Ajout impossible.")
            # Ajout en lot
            with st.expander("Ajouter plusieurs élèves"):
                multi = st.text_area("Entrez des prénoms (séparés par virgules ou retours à la ligne)", key="cls_add_multi")
                if st.button("Ajouter ces élèves", key="cls_add_multi_btn"):
                    names = []
                    for part in (multi or "").replace(";", ",").split(","):
                        names.extend([p.strip() for p in part.split("\n")])
                    names = [n for n in names if n]
                    if not names:
                        st.info("Rien à ajouter.")
                    else:
                        added = 0
                        for nm in names:
                            ok, _ = add_student_db(t["id"], nm)
                            if ok:
                                added += 1
                        st.session_state.students = list_students_db(t["id"])
                        st.success(f"{added} élève(s) ajouté(s).")
            # Liste des élèves
            if st.session_state.students:
                st.markdown("#### Liste des élèves")
                for s in st.session_state.students:
                    c1, c2 = st.columns([4,1])
                    with c1:
                        st.write(s["name"])
                    with c2:
                        st.markdown(f'<a class="trash-btn" href="?del_student={s["id"]}" title="Supprimer">🗑️</a>', unsafe_allow_html=True)
            else:
                st.info("Aucun élève enregistré pour l'instant.")
        st.divider()
        st.header("📋 Observations validées")
        if st.session_state.observations:
            for i, obs in enumerate(st.session_state.observations):
                _title_appr = (obs.get('Apprentissage') or obs.get('Critère') or "")
                row_left, row_right = st.columns([9, 1])
                with row_left:
                    expander = st.expander(f"Observation {i+1} - {_title_appr[:30]}...")
                with row_right:
                    if obs.get("db_id"):
                        st.markdown(f'<a class="trash-btn" href="?del_obs={obs["db_id"]}" title="Supprimer">🗑️</a>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<a class="trash-btn" href="?del_idx={i}" title="Supprimer">🗑️</a>', unsafe_allow_html=True)
                with expander:
                    st.markdown(f"**Domaine** : {obs['Domaine']}")
                    st.markdown(f"**Mode** : {obs['Mode']}")
                    st.markdown(f"**Observables** :")
                    for o in obs["Observables"]:
                        st.markdown(f"- {o}")
                    if obs.get("Activités"):
                        st.markdown("**Activités réalisées** :")
                        for a in obs["Activités"]:
                            st.markdown(f"- {a}")
                    if obs.get("Compétences_mobilisées") or obs.get("Processus_mobilisés"):
                        st.markdown("**Mobilisation prévue** :")
                        if obs.get("Compétences_mobilisées"):
                            st.markdown("- Compétences transversales : " + ", ".join(obs["Compétences_mobilisées"]))
                        if obs.get("Processus_mobilisés"):
                            st.markdown("- Processus cognitifs : " + ", ".join(obs["Processus_mobilisés"]))
                    if obs["Commentaire"]:
                        st.markdown(f"**Commentaire** : {obs['Commentaire']}")
                    if obs.get("Compétence_mise_en_avant") or obs.get("Processus_mis_en_avant"):
                        st.markdown("**Mise en avant** :")
                        if obs.get("Compétence_mise_en_avant"):
                            st.markdown(f"- Compétence transversale : {obs['Compétence_mise_en_avant']}")
                        if obs.get("Processus_mis_en_avant"):
                            st.markdown(f"- Processus cognitif : {obs['Processus_mis_en_avant']}")
            
            # Génération et téléchargement PDF
            pdf_buffer = BytesIO()
            pdf = CustomPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_margins(15, 15, 15)
            pdf.alias_nb_pages()
            # Fonts: try Unicode TrueType to support accents
            try:
                pdf.add_font("ArialUnicode", "", "C:\\Windows\\Fonts\\arial.ttf", uni=True)
                pdf.add_font("ArialUnicode", "B", "C:\\Windows\\Fonts\\arialbd.ttf", uni=True)
                base_font = "ArialUnicode"
            except Exception:
                base_font = "Helvetica"
            pdf.add_page()

            content_width = getattr(pdf, "epw", pdf.w - pdf.l_margin - pdf.r_margin)
            pdf.set_font(base_font, "", 12)
            date_str = datetime.now().strftime("%d/%m/%Y")
            date_filename = datetime.now().strftime("%Y-%m-%d_%H-%M")

            # Observations
            obs_on_page = 0
            for obs in st.session_state.observations:
                # Contrainte de pagination: max 1 observation par page, éviter le footer
                safe_bottom = getattr(pdf, 'b_margin', 15) + 20
                if obs_on_page >= 1 or pdf.get_y() > (pdf.h - safe_bottom - 120):
                    pdf.add_page()
                    obs_on_page = 0
                # Début du bloc avec encadrement
                x_box = pdf.l_margin
                y_box = pdf.get_y()
                # Titre d'observation (bandeau cyan arrondi) avec retour à la ligne si trop long
                pdf.set_font(base_font, "B", 13)
                pdf.set_text_color(255, 255, 255)
                pdf.set_fill_color(0, 173, 239)
                title_h = 8
                # Calcul de la hauteur nécessaire
                title_text = (obs.get('Apprentissage') or obs.get('Critère') or "")
                req_h = pdf.calculate_multicell_height(title_text, content_width - 4, 6)
                # Plus d'espace bas dans le bandeau pour aérer
                block_h = max(title_h, req_h + 3)
                # Utiliser un bandeau à coins arrondis en haut uniquement, aligné avec le cadre
                frame_x = pdf.l_margin + 3
                frame_w = content_width - 6
                pdf.rounded_top_rect(frame_x, y_box, frame_w, block_h, r=3, style='F')
                # Positionner plus haut (padding haut faible, bas plus large)
                pdf.set_xy(frame_x + 2, y_box + 1)
                pdf.multi_cell(frame_w - 4, 6, title_text)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(base_font, "", 11)
                pdf.ln(2)

                # Caractéristiques avec libellés en gras (décalées vers l'intérieur du cadre)
                pdf.set_x(frame_x + 2); pdf.set_font(base_font, "B", 11); pdf.write(6, "Domaine: "); pdf.set_font(base_font, "", 11); pdf.write(6, (obs['Domaine'] or "") + "\n")
                pdf.set_x(frame_x + 2); pdf.set_font(base_font, "B", 11); pdf.write(6, "Composante: "); pdf.set_font(base_font, "", 11); pdf.write(6, (obs['Composante'] or "") + "\n")
                # Suppression de la ligne Mode (inutile)
                if obs.get("Activités"):
                    pdf.set_x(frame_x + 2); pdf.set_font(base_font, "B", 11); pdf.write(6, "Activités réalisées: "); pdf.set_font(base_font, "", 11); pdf.write(6, ", ".join(obs['Activités']) + "\n")
                if obs.get("Compétences_mobilisées"):
                    pdf.set_x(frame_x + 2); pdf.set_font(base_font, "B", 11); pdf.write(6, "Compétences transversales mobilisées: "); pdf.set_font(base_font, "", 11); pdf.write(6, ", ".join(obs['Compétences_mobilisées']) + "\n")
                if obs.get("Processus_mobilisés"):
                    pdf.set_x(frame_x + 2); pdf.set_font(base_font, "B", 11); pdf.write(6, "Processus cognitifs mobilisés: "); pdf.set_font(base_font, "", 11); pdf.write(6, ", ".join(obs['Processus_mobilisés']) + "\n")
                # Observables: Likert horizontal avec emoji + habillage
                if obs.get("Observables"):
                    pdf.ln(1)
                    pdf.set_x(frame_x + 2); pdf.set_font(base_font, "B", 11); pdf.write(6, "Observables\n")
                    pdf.set_font(base_font, "", 11)
                    # Dimensions pour l'échelle
                    scale_box_w = 14
                    scale_box_h = 12
                    scale_gap = 6
                    scale_total_w = 3 * (scale_box_w + scale_gap) - scale_gap
                    right_padding = 6  # espace entre l'échelle et le cadre à droite
                    text_w = frame_w - scale_total_w - 6 - right_padding
                    # Grouper les observables par (label, niveau)
                    groups = {}
                    order = []
                    for item in obs["Observables"]:
                        subject = "Classe"
                        raw = item
                        if ":" in raw:
                            parts = raw.split(":", 1)
                            subject = parts[0].strip()
                            raw = parts[1].strip()
                        idx = 1
                        if ("Encore en train de germer" in raw):
                            idx = 0
                        elif ("Épanoui" in raw):
                            idx = 2
                        else:
                            idx = 1
                        label = raw
                        if " - " in raw:
                            label = raw.split(" - ", 1)[1].strip()
                        key = (label, idx)
                        if key not in groups:
                            groups[key] = {"names": [], "has_class": False}
                            order.append(key)
                        if subject.lower() == "classe":
                            groups[key]["has_class"] = True
                        else:
                            if subject not in groups[key]["names"]:
                                groups[key]["names"].append(subject)

                    # Rendu groupé: un label par ligne, sujets listés avec virgules et retour à la ligne si long
                    for (label, idx) in order:
                        y_line = pdf.get_y()
                        names = groups[(label, idx)]["names"]
                        has_class = groups[(label, idx)]["has_class"]
                        subject_text_parts = []
                        if has_class:
                            subject_text_parts.append("Classe")
                        if names:
                            subject_text_parts.append(", ".join(names))
                        subject_text = ", ".join(subject_text_parts) if subject_text_parts else "Classe"

                        pdf.set_font(base_font, "", 11)
                        label_h = pdf.calculate_multicell_height(label, text_w, 6)
                        pdf.set_font(base_font, "", 10)
                        subj_h = pdf.calculate_multicell_height(subject_text, text_w, 5)
                        row_h = max(label_h + subj_h + 3, scale_box_h + 6)

                        # Fond de ligne aligné avec le cadre
                        pdf.set_fill_color(255, 255, 255)
                        pdf.rounded_rect(frame_x, y_line, frame_w, row_h, r=1.5, style='F')

                        # Libellé
                        pdf.set_font(base_font, "", 11)
                        pdf.set_xy(frame_x + 2, y_line + 1)
                        pdf.multi_cell(text_w, 6, label, align='L')

                        # Sujet(s) sous le libellé, avec retour à la ligne si nécessaire
                        pdf.set_text_color(90, 90, 90)
                        pdf.set_font(base_font, "", 10)
                        pdf.set_xy(frame_x + 2, y_line + 1 + label_h)
                        pdf.multi_cell(text_w, 5, subject_text, align='L')
                        pdf.set_text_color(0, 0, 0)
                        pdf.set_font(base_font, "", 11)

                        # Échelle à droite
                        pdf.draw_likert_scale(idx, x=frame_x + text_w + 6, y=y_line + 2, box_w=scale_box_w, box_h=scale_box_h, gap=scale_gap)

                        # Avancer sous le bloc
                        pdf.set_y(y_line + row_h)
                if obs.get("Commentaire"):
                    # Séparer commentaire classe vs individus (si le texte contient des préfixes)
                    comment_lines = [l.strip() for l in str(obs['Commentaire']).replace("\r", "\n").split("\n") if l.strip()]
                    student_names = []
                    for it in obs.get("Observables", []):
                        if ":" in it:
                            nm = it.split(":", 1)[0].strip()
                            if nm and nm not in student_names:
                                student_names.append(nm)
                    class_comments = []
                    student_comments = {}
                    for l in comment_lines:
                        # ignorer des lignes de type "Nom: ... - ..." (valeurs Likert)
                        if (":" in l and " - " in l):
                            continue
                        lower = l.lower()
                        if lower.startswith("classe:"):
                            class_comments.append(l.split(":", 1)[1].strip())
                            continue
                        matched = False
                        for nm in student_names:
                            if l.startswith(nm + ":"):
                                student_comments.setdefault(nm, []).append(l.split(":", 1)[1].strip())
                                matched = True
                                break
                        if not matched:
                            class_comments.append(l)
                    if class_comments:
                        # Faire la ligne vide avec ln() puis conserver le même x
                        pdf.ln(1)
                        pdf.set_x(frame_x + 2); pdf.set_font(base_font, "B", 11); pdf.write(6, "Commentaire: ")
                        pdf.set_font(base_font, "", 11); pdf.write(6, " ".join(class_comments) + "\n")
                        if student_comments:
                            pdf.set_x(frame_x + 2); pdf.set_font(base_font, "B", 11); pdf.write(6, "Commentaire (élèves):\n")
                            pdf.set_font(base_font, "", 11)
                            for nm, notes in student_comments.items():
                                pdf.set_x(frame_x + 4); pdf.write(6, f"- {nm}: {' '.join(notes)}\n")
                    if obs.get("Compétence_mise_en_avant") or obs.get("Processus_mis_en_avant"):
                        pdf.ln(1)
                        pdf.set_x(frame_x + 2); pdf.set_font(base_font, "B", 11); pdf.write(6, "Compétences transversales et processus cognitifs mis en avant\n")
                        pdf.set_font(base_font, "", 11)
                        if obs.get("Compétence_mise_en_avant"):
                            pdf.set_x(frame_x + 4); pdf.write(6, f"- Compétence transversale: {obs['Compétence_mise_en_avant']}\n")
                        if obs.get("Processus_mis_en_avant"):
                            pdf.set_x(frame_x + 4); pdf.write(6, f"- Processus cognitif: {obs['Processus_mis_en_avant']}\n")

                # Encadrement arrondi autour du bloc
                y_after = pdf.get_y()
                box_h = y_after - y_box
                pdf.set_draw_color(0, 0, 0)
                # Bordure plus épaisse et parfaitement alignée avec le titre
                pdf.set_line_width(0.6)
                pdf.rounded_rect(frame_x, y_box, frame_w, box_h, r=3, style='D')
                pdf.set_line_width(0.2)
                pdf.ln(6)
                obs_on_page += 1

            pdf_output = bytes(pdf.output(dest='S'))
            pdf_buffer.write(pdf_output)
            pdf_buffer.seek(0)

            st.download_button(
                label="Télécharger le rapport PDF",
                data=pdf_buffer,
                file_name=f"fichet_{date_filename}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("Aucune observation validée pour l'instant.")

# --- Footer institutionnel ---
left_spacer, center_col, right_spacer = st.columns([1, 2, 1])
with center_col:
    inner_left, content_col, inner_right = st.columns([1, 8, 1])
    with content_col:
        logo_col, text_col = st.columns([1, 8])
        with logo_col:
            logo_path = Path(__file__).parent / "images" / "logo_geneve.jpg"
            st.image(str(logo_path), width=64)
        with text_col:
            st.markdown("<br/>**Direction générale de l'enseignement obligatoire**<br/>Service enseignement et évaluation", unsafe_allow_html=True)