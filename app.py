import streamlit as st
from fpdf import FPDF
from io import BytesIO
from datetime import datetime

# --- Données enrichies avec les 7 domaines, compétences transversales et processus cognitifs ---
domaines = {
    "Corps et motricité": {
        "icon": "🏃",
        "composantes": {
            "Motricité globale": {
                "Sauter sur un pied": {
                    "Activités par contexte": {
                        "En classe": ["Parcours entre les tables en sautant à cloche-pied", "Jeu du flamant rose (tenir la position)"],
                        "Sur le banc": ["Sauter d’un banc à l’autre (faible hauteur)", "Équilibre sur un pied pendant 5 secondes"],
                        "Jeu à faire semblant": ["Imiter un kangourou dans la savane", "Pirate avec une jambe de bois"],
                        "Dehors": ["Sauter dans les cerceaux au sol", "Course à cloche-pied dans la cour"],
                        "Autres": ["Atelier motricité en EPS", "Jeux libres avec consigne motrice"]
                    },
                    "Observables": ["Tient l’équilibre ≥ 3 sec", "Change de pied spontanément", "Ne tombe pas"],
                    "compétences_transversales": ["Persévérance", "Estime de soi", "Régulation émotionnelle"],
                    "processus_cognitifs": ["Attention soutenue", "Contrôle inhibiteur", "Planification motrice"]
                },
                "Courir et s'arrêter": {
                    "Activités par contexte": {
                        "En classe": ["Course entre les chaises avec arrêt au signal", "Jeu du feu vert/feu rouge"],
                        "Sur le banc": ["Marche rapide puis arrêt net", "Déplacement contrôlé"],
                        "Jeu à faire semblant": ["Livrer un message urgent au roi", "Échapper au dragon puis se figer"],
                        "Dehors": ["Relais avec départ/arrêt", "Course avec plots et arrêt sur cible"],
                        "Autres": ["Jeux sportifs collectifs", "Ateliers EPS"]
                    },
                    "Observables": ["Freine sans glisser", "S’arrête pile sur la cible", "Contrôle sa vitesse"],
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
                "Compter jusqu’à 10 avec correspondance terme à terme": {
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
    },
    "Santé globale": {
        "icon": "🍏",
        "composantes": {
            "Hygiène et bien-être": {
                "Se laver les mains correctement": {
                    "Activités par contexte": {
                        "En classe": ["Chanson du lavage de mains", "Affiche séquentielle"],
                        "Sur le banc": ["Discussion : 'Pourquoi se laver les mains ?'"],
                        "Jeu à faire semblant": ["Docteur ou cuisinier", "Poupée qui apprend à se laver"],
                        "Dehors": ["Lavage après jardinage", "Rituel avant le goûter"],
                        "Autres": ["Atelier santé", "Visite d’un professionnel"]
                    },
                    "Observables": ["Utilise du savon", "Frotte toutes les parties", "Se sèche les mains"],
                    "compétences_transversales": ["Autonomie", "Responsabilité", "Soins de soi"],
                    "processus_cognitifs": ["Mémoire procédurale", "Séquençage", "Autocontrôle"]
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

# --- Interface principale ---
st.set_page_config(page_title="Enseigner et évaluer en 1P-2P", layout="wide")
st.title("📚 Enseigner & Évaluer en 1P-2P")

# --- Formulaire d’observation dynamique ---
for domaine, data in domaines.items():
    icon = data["icon"]
    with st.expander(f"{icon} **{domaine}**", expanded=False):
        for comp_name, criteres in data["composantes"].items():
            with st.expander(f"🟢 **Composante : {comp_name}**", expanded=False):
                for crit_name, detail in criteres.items():
                    with st.expander(f"🔹 **Critère : {crit_name}**", expanded=False):
                        
                        # Compétences transversales & processus cognitifs
                        st.markdown("### 🧠 Compétences transversales & Processus cognitifs")
                        st.markdown(f"- **Compétences transversales** : {', '.join(detail['compétences_transversales'])}")
                        st.markdown(f"- **Processus cognitifs** : {', '.join(detail['processus_cognitifs'])}")
                        st.markdown("---")

                        # Activités pédagogiques
                        st.markdown("### 🎯 Idées d’activités pédagogiques")
                        contextes = ["En classe", "Sur le banc", "Jeu à faire semblant", "Dehors", "Autres"]
                        for ctx in contextes:
                            if ctx in detail["Activités par contexte"]:
                                activites = detail["Activités par contexte"][ctx]
                                st.markdown(f"**{ctx} :**")
                                for act in activites:
                                    st.markdown(f"- {act}")
                        st.markdown("---")

                        # Observables
                        st.markdown("### 👀 Observables à évaluer")
                        observables = detail["Observables"]

                        # Choix dynamique : classe entière ou élèves
                        mode_obs = st.radio(
                            "Mode d’observation",
                            ("Toute la classe", "Élèves sélectionnés"),
                            key=f"mode_{domaine}_{comp_name}_{crit_name}",
                            horizontal=True
                        )

                        eleves_a_observer = []
                        if mode_obs == "Élèves sélectionnés":
                            eleves_input = st.text_input(
                                "Liste des élèves (séparés par des virgules)",
                                key=f"eleves_{domaine}_{comp_name}_{crit_name}"
                            )
                            if eleves_input:
                                eleves_a_observer = [e.strip() for e in eleves_input.split(",") if e.strip()]
                        else:
                            eleves_a_observer = ["Toute la classe"]

                        # Affichage des checkboxes
                        selected_observables = []
                        if mode_obs == "Toute la classe":
                            for obs in observables:
                                if st.checkbox(obs, key=f"classe_{domaine}_{comp_name}_{crit_name}_{obs}"):
                                    selected_observables.append(obs)
                        else:
                            for obs in observables:
                                st.markdown(f"**{obs}**")
                                for eleve in eleves_a_observer:
                                    if st.checkbox(eleve, key=f"eleve_{domaine}_{comp_name}_{crit_name}_{obs}_{eleve}"):
                                        selected_observables.append(f"{eleve}: {obs}")

                        # Commentaire
                        comment_key = f"comment_{domaine}_{comp_name}_{crit_name}"
                        commentaire = st.text_input("Commentaire (facultatif)", key=comment_key)

                        # Bouton de validation
                        if st.button("✅ Valider cette observation", key=f"valider_{domaine}_{comp_name}_{crit_name}"):
                            if selected_observables:
                                obs_entry = {
                                    "Domaine": domaine,
                                    "Composante": comp_name,
                                    "Critère": crit_name,
                                    "Mode": mode_obs,
                                    "Observables": selected_observables.copy(),
                                    "Commentaire": commentaire or ""
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
                    if obs["Commentaire"]:
                        st.markdown(f"**Commentaire** : {obs['Commentaire']}")
            
            # Génération et téléchargement PDF
            pdf_buffer = BytesIO()
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_margins(15, 15, 15)
            # Fonts: try Unicode TrueType to support accents, guillemets, ≥, …
            try:
                pdf.add_font("ArialUnicode", "", "C:\\Windows\\Fonts\\arial.ttf", uni=True)
                pdf.add_font("ArialUnicode", "B", "C:\\Windows\\Fonts\\arialbd.ttf", uni=True)
                base_font = "ArialUnicode"
            except Exception:
                # Fallback to core font if system fonts are unavailable
                base_font = "Helvetica"
            pdf.add_page()
            pdf.set_font(base_font, "B", 16)
            pdf.cell(0, 10, "Rapport de la séance", ln=True, align="C")
            pdf.ln(10)

            pdf.set_font(base_font, "", 12)
            pdf.set_x(pdf.l_margin)
            content_width = getattr(pdf, "epw", pdf.w - pdf.l_margin - pdf.r_margin)
            # Date du rapport
            date_str = datetime.now().strftime("%d/%m/%Y")
            date_filename = datetime.now().strftime("%Y-%m-%d")
            pdf.set_x(pdf.l_margin); pdf.multi_cell(content_width, 8, f"Date: {date_str}", align='L')
            pdf.ln(5)
            for obs in st.session_state.observations:
                pdf.set_x(pdf.l_margin); pdf.multi_cell(content_width, 8, f"Domaine: {obs['Domaine']}", align='L')
                pdf.set_x(pdf.l_margin); pdf.multi_cell(content_width, 8, f"Composante: {obs['Composante']}", align='L')
                pdf.set_x(pdf.l_margin); pdf.multi_cell(content_width, 8, f"Critère: {obs['Critère']}", align='L')
                pdf.set_x(pdf.l_margin); pdf.multi_cell(content_width, 8, f"Mode: {obs['Mode']}", align='L')
                pdf.set_x(pdf.l_margin); pdf.multi_cell(content_width, 8, f"Observables: {', '.join(obs['Observables'])}", align='L')
                if obs["Commentaire"]:
                    pdf.set_x(pdf.l_margin); pdf.multi_cell(content_width, 8, f"Commentaire: {obs['Commentaire']}", align='L')
                pdf.ln(5)

            pdf_output = bytes(pdf.output(dest='S'))
            pdf_buffer.write(pdf_output)
            pdf_buffer.seek(0)

            st.download_button(
                label="Télécharger le rapport PDF",
                data=pdf_buffer,
                file_name=f"rapport_seance_{date_filename}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("Aucune observation validée pour l’instant.")