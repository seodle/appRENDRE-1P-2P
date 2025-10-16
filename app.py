import streamlit as st
from fpdf import FPDF
from io import BytesIO
from datetime import datetime
from pathlib import Path
import base64

# --- PDF amélioré avec en-tête/pied-de-page et éléments graphiques ---
class CustomPDF(FPDF):
    def __init__(self, teacher_name: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maitre = teacher_name
        self.first_page = True
        self.images_dir = Path(__file__).parent / "images"

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
        self.cell(0, 10, "Fichet de séance", align="C")   

        # (Nom enseignant non affiché)

        # Bannière
        x_rect, y_rect, w_rect, h_rect, radius = 10, 30, 190, 15, 5
        self.set_fill_color(0, 173, 239)
        self.set_draw_color(0, 173, 239)
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", "B", 16)
        self.rounded_rect(x_rect, y_rect, w_rect, h_rect, r=radius, style='DF')
        self.set_xy(x_rect, y_rect + 3)
        self.cell(w_rect, h_rect - 6, "Synthèse des informations", 0, 0, "C")

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

# --- Bouton flèche fixe en haut à droite ---
st.markdown(
    """
    <style>
    .fixed-arrow {
        position: fixed;
        top: 10px;
        right: 10px;
        z-index: 999;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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

# --- Interface principale ---
st.set_page_config(page_title="Évaluer et enseigner en 1P-2P", layout="wide")

# Header avec date
col1, col2 = st.columns([3, 1])
with col1:
    st.title("Évaluer et enseigner en 1P-2P")
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
                        crit_expander = st.expander(f"🔹 **Critère : {crit_name}**", expanded=False)
                    with code_col:
                        if code_per:
                            st.markdown(f'<span style="color:red; font-weight:bold; font-size:1rem;">{code_per}</span>', unsafe_allow_html=True)
                    
                    with crit_expander:
                        # Section déplacée dans l'onglet Enseigner

                        tab_enseigner, tab_evaluer = st.tabs(["🧑‍🏫 Enseigner", "👀 Évaluer"])

                        with tab_enseigner:

                            st.markdown("#### 🧠 Compétences transversales & Processus cognitifs")
                            st.markdown(f"- **Compétences transversales mobilisables** : {', '.join(detail['compétences_transversales'])}")
                            st.markdown(f"- **Processus cognitifs que l'on peut renforcer** : {', '.join(detail['processus_cognitifs'])}")
                            st.markdown("#### 🎯 Idées d'activités pédagogiques")
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
                                st.markdown(f"**{obs}**")
                                slider_col, _ = st.columns([4, 8])
                                with slider_col:
                                    value = st.select_slider(
                                        "",
                                        options=scale_options,
                                        key=f"{domaine}_{comp_name}_{crit_name}_{obs}_rating",
                                        label_visibility="collapsed"
                                    )
                                apply_mode = st.selectbox(
                                    "Appliquer à",
                                    ("Toute la classe", "Élèves particuliers"),
                                    key=f"apply_{domaine}_{comp_name}_{crit_name}_{obs}"
                                )
                                if apply_mode == "Toute la classe":
                                    selected_observables.append(f"{value} - {obs}")
                                else:
                                    # Liste dynamique d'élèves par observable
                                    list_key = f"eleves_list_{domaine}_{comp_name}_{crit_name}_{obs}"
                                    input_key = f"eleves_input_{domaine}_{comp_name}_{crit_name}_{obs}"
                                    if list_key not in st.session_state:
                                        st.session_state[list_key] = []
                                    st.text_input(
                                        "Ajouter un élève (Entrée pour valider)",
                                        key=input_key,
                                        on_change=add_student_to_list,
                                        args=(list_key, input_key)
                                    )
                                    # Affichage compact des élèves saisis
                                    if st.session_state[list_key]:
                                        st.markdown(
                                            ", ".join(st.session_state[list_key])
                                        )
                                    # Enregistrer une entrée par élève
                                    for eleve in st.session_state[list_key]:
                                        selected_observables.append(f"{eleve}: {value} - {obs}")

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
                                    obs_entry = {
                                        "Domaine": domaine,
                                        "Composante": comp_name,
                                        "Critère": crit_name,
                                        "Mode": "Selon sélection (classe/élèves)",
                                        "Observables": selected_observables.copy(),
                                        "Commentaire": commentaire or "",
                                        "Activités": selected_activities,
                                        "Compétence_mise_en_avant": (comp_selected if comp_selected != "—" else ""),
                                        "Processus_mis_en_avant": (proc_selected if proc_selected != "—" else "")
                                    }
                                    st.session_state.observations.append(obs_entry)
                                    st.success("Observation enregistrée !")

# --- Sidebar dynamique ---
with st.sidebar:
        st.header("📋 Observations validées")
        if st.session_state.observations:
            for i, obs in enumerate(st.session_state.observations):
                with st.expander(f"Observation {i+1} - {obs['Critère'][:30]}..."):
                    st.markdown(f"**Domaine** : {obs['Domaine']}")
                    st.markdown(f"**Mode** : {obs['Mode']}")
                    st.markdown(f"**Observables** :")
                    for o in obs["Observables"]:
                        st.markdown(f"- {o}")
                    if obs.get("Activités"):
                        st.markdown("**Activités réalisées** :")
                        for a in obs["Activités"]:
                            st.markdown(f"- {a}")
                    if obs["Commentaire"]:
                        st.markdown(f"**Commentaire** : {obs['Commentaire']}")
                    if obs.get("Compétence_mise_en_avant") or obs.get("Processus_mis_en_avant"):
                        st.markdown("**Mise en avant** :")
                        if obs.get("Compétence_mise_en_avant"):
                            st.markdown(f"- Compétence transversale : {obs['Compétence_mise_en_avant']}")
                        if obs.get("Processus_mis_en_avant"):
                            st.markdown(f"- Processus cognitif : {obs['Processus_mis_en_avant']}")
            
            # Génération et téléchargement PDF (version améliorée)
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
            # Date juste après la bannière, sans libellé
            pdf.set_x(pdf.l_margin); pdf.multi_cell(content_width, 7, date_str)
            pdf.ln(3)

            # Observations
            for obs in st.session_state.observations:
                # Début du bloc avec encadrement
                x_box = pdf.l_margin
                y_box = pdf.get_y()
                # Titre d'observation (bandeau cyan)
                pdf.set_font(base_font, "B", 13)
                pdf.set_text_color(255, 255, 255)
                pdf.set_fill_color(0, 173, 239)
                pdf.cell(0, 8, obs['Critère'], 0, 1, 'L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font(base_font, "", 11)
                pdf.ln(2)

                # Caractéristiques avec libellés en gras
                pdf.set_x(pdf.l_margin); pdf.set_font(base_font, "B", 11); pdf.write(6, "Domaine: "); pdf.set_font(base_font, "", 11); pdf.write(6, (obs['Domaine'] or "") + "\n")
                pdf.set_x(pdf.l_margin); pdf.set_font(base_font, "B", 11); pdf.write(6, "Composante: "); pdf.set_font(base_font, "", 11); pdf.write(6, (obs['Composante'] or "") + "\n")
                pdf.set_x(pdf.l_margin); pdf.set_font(base_font, "B", 11); pdf.write(6, "Mode: "); pdf.set_font(base_font, "", 11); pdf.write(6, (obs['Mode'] or "") + "\n")
                if obs.get("Activités"):
                    pdf.set_x(pdf.l_margin); pdf.set_font(base_font, "B", 11); pdf.write(6, "Activités réalisées: "); pdf.set_font(base_font, "", 11); pdf.write(6, ", ".join(obs['Activités']) + "\n")
                if obs.get("Observables"):
                    pdf.set_x(pdf.l_margin); pdf.set_font(base_font, "B", 11); pdf.write(6, "Observables: "); pdf.set_font(base_font, "", 11); pdf.write(6, ", ".join(obs['Observables']) + "\n")
                if obs.get("Commentaire"):
                    pdf.set_x(pdf.l_margin); pdf.set_font(base_font, "B", 11); pdf.write(6, "Commentaire: "); pdf.set_font(base_font, "", 11); pdf.write(6, obs['Commentaire'] + "\n")
                if obs.get("Compétence_mise_en_avant") or obs.get("Processus_mis_en_avant"):
                    pdf.ln(1)
                    pdf.set_x(pdf.l_margin); pdf.set_font(base_font, "B", 11); pdf.write(6, "Mise en avant\n")
                    pdf.set_font(base_font, "", 11)
                    if obs.get("Compétence_mise_en_avant"):
                        pdf.set_x(pdf.l_margin); pdf.write(6, f"- Compétence transversale: {obs['Compétence_mise_en_avant']}\n")
                    if obs.get("Processus_mis_en_avant"):
                        pdf.set_x(pdf.l_margin); pdf.write(6, f"- Processus cognitif: {obs['Processus_mis_en_avant']}\n")

                # Encadrement arrondi autour du bloc
                y_after = pdf.get_y()
                box_w = content_width
                box_h = y_after - y_box
                pdf.set_draw_color(0, 0, 0)
                pdf.rounded_rect(x_box, y_box, box_w, box_h, r=3, style='D')
                pdf.ln(4)

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