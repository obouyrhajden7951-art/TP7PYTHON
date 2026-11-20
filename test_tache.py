"""
test_tache.py - Tests unitaires de tache.py

Lancer avec :  python -m unittest test_tache -v
"""

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta

from tache import (
    Tache,
    ValidationMixin,
    HistoriqueMixin,
    JournalisationMixin,
)


def capturer(fonction, *args):
    """Exécute fonction(*args) et retourne tout ce qu'elle a affiché (print)."""
    tampon = io.StringIO()
    with redirect_stdout(tampon):  # redirige print vers le tampon
        fonction(*args)
    return tampon.getvalue()


# ======================================================================
# 1) CRÉATION
# ======================================================================
class TestCreation(unittest.TestCase):
    def test_creation_valide(self):
        with redirect_stdout(io.StringIO()):  # masque le journal de création
            t = Tache("Rapport", "Brouillon")
        self.assertEqual(t.titre, "Rapport")
        self.assertEqual(t.description, "Brouillon")

    def test_description_par_defaut_vide(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(Tache("A").description, "")

    def test_date_creation_est_recente(self):
        avant = datetime.now()
        with redirect_stdout(io.StringIO()):
            t = Tache("A")
        self.assertIsInstance(t.date_creation, datetime)
        self.assertTrue(avant <= t.date_creation <= datetime.now() + timedelta(seconds=1))

    def test_historique_vide_au_depart(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(Tache("A").historique, ())


# ======================================================================
# 2) VALIDATION DU TITRE (ValidationMixin)
# ======================================================================
class TestValidation(unittest.TestCase):
    def test_titre_none(self):
        with self.assertRaises(ValueError):
            Tache(None)

    def test_titre_vide_ou_espaces(self):
        for titre in ("", "   ", "\t\n"):
            with self.subTest(titre=titre):
                with self.assertRaises(ValueError):
                    Tache(titre)

    def test_titre_mauvais_type(self):
        for titre in (123, 4.5, ["a"], True):
            with self.subTest(titre=titre):
                with self.assertRaises(TypeError):
                    Tache(titre)

    def test_description_mauvais_type(self):
        for desc in (None, 12, ["x"]):
            with self.subTest(desc=desc):
                with self.assertRaises(TypeError):
                    Tache("A", desc)

    def test_titre_toujours_valide_apres_creation(self):
        # Le titre est protégé aussi APRÈS la création
        with redirect_stdout(io.StringIO()):
            t = Tache("Valide")
        with self.assertRaises(ValueError):
            t.titre = ""
        with self.assertRaises(ValueError):
            t.titre = None
        self.assertEqual(t.titre, "Valide")  # inchangé après l'échec

    def test_titre_modifiable_si_valide(self):
        with redirect_stdout(io.StringIO()):
            t = Tache("Ancien")
        t.titre = "Nouveau"
        self.assertEqual(t.titre, "Nouveau")

    def test_valider_explicite(self):
        with redirect_stdout(io.StringIO()):
            t = Tache("OK")
        t.valider()  # ne doit rien lever


# ======================================================================
# 3) MISE À JOUR ET HISTORIQUE (HistoriqueMixin)
# ======================================================================
class TestMiseAJour(unittest.TestCase):
    def setUp(self):
        with redirect_stdout(io.StringIO()):
            self.t = Tache("Tâche", "v1")

    def test_mise_a_jour_change_la_description(self):
        with redirect_stdout(io.StringIO()):
            self.t.mettre_a_jour("v2")
        self.assertEqual(self.t.description, "v2")

    def test_ancienne_version_conservee(self):
        with redirect_stdout(io.StringIO()):
            self.t.mettre_a_jour("v2")
        self.assertEqual(len(self.t.historique), 1)
        date, ancienne = self.t.historique[0]
        self.assertEqual(ancienne, "v1")
        self.assertIsInstance(date, datetime)

    def test_plusieurs_versions_dans_l_ordre(self):
        with redirect_stdout(io.StringIO()):
            self.t.mettre_a_jour("v2")
            self.t.mettre_a_jour("v3")
            self.t.mettre_a_jour("v4")
        anciennes = [d for _, d in self.t.historique]
        self.assertEqual(anciennes, ["v1", "v2", "v3"])  # v4 = version courante
        self.assertEqual(self.t.description, "v4")

    def test_meme_description_est_enregistree(self):
        with redirect_stdout(io.StringIO()):
            self.t.mettre_a_jour("v1")
        self.assertEqual(len(self.t.historique), 1)

    def test_historique_en_lecture_seule(self):
        # Le tuple retourné ne peut pas être modifié depuis l'extérieur
        with self.assertRaises(AttributeError):
            self.t.historique.append(("x", "y"))
        with self.assertRaises(AttributeError):
            self.t.historique = []  # property sans setter

    def test_echec_ne_modifie_rien(self):
        # Description invalide : ni description ni historique ne changent
        with self.assertRaises(TypeError):
            self.t.mettre_a_jour(None)
        self.assertEqual(self.t.description, "v1")
        self.assertEqual(self.t.historique, ())


# ======================================================================
# 4) AFFICHAGE DE L'HISTORIQUE
# ======================================================================
class TestAfficherHistorique(unittest.TestCase):
    def test_historique_vide(self):
        with redirect_stdout(io.StringIO()):
            t = Tache("Vide", "v1")
        sortie = capturer(t.afficher_historique)
        self.assertIn("Aucun historique", sortie)

    def test_historique_non_vide(self):
        with redirect_stdout(io.StringIO()):
            t = Tache("Plan", "v1")
            t.mettre_a_jour("v2")
            t.mettre_a_jour("v3")
        sortie = capturer(t.afficher_historique)
        self.assertIn("Historique de 'Plan'", sortie)
        self.assertIn("v1 (", sortie)
        self.assertIn(": v1", sortie)
        self.assertIn(": v2", sortie)
        self.assertNotIn(": v3", sortie)  # v3 = version courante, pas archivée


# ======================================================================
# 5) JOURNALISATION (JournalisationMixin)
# ======================================================================
class TestJournal(unittest.TestCase):
    def test_journal_creation(self):
        sortie = capturer(Tache, "Rapport", "x")
        self.assertIn("[Journal]", sortie)
        self.assertIn("Création de la tâche 'Rapport'", sortie)

    def test_journal_mise_a_jour(self):
        with redirect_stdout(io.StringIO()):
            t = Tache("Rapport", "x")
        sortie = capturer(t.mettre_a_jour, "y")
        self.assertIn("Mise à jour de la tâche 'Rapport'", sortie)

    def test_pas_de_journal_si_echec(self):
        with redirect_stdout(io.StringIO()):
            t = Tache("Rapport", "x")
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            with self.assertRaises(TypeError):
                t.mettre_a_jour(5)
        self.assertEqual(tampon.getvalue(), "")


# ======================================================================
# 6) STRUCTURE : MIXINS INDÉPENDANTS ET RÉUTILISABLES
# ======================================================================
class TestStructure(unittest.TestCase):
    def test_heritage_direct_des_trois_mixins(self):
        self.assertEqual(
            Tache.__bases__,
            (ValidationMixin, HistoriqueMixin, JournalisationMixin),
        )

    def test_mro(self):
        noms = [c.__name__ for c in Tache.__mro__]
        self.assertEqual(
            noms,
            ["Tache", "ValidationMixin", "HistoriqueMixin",
             "JournalisationMixin", "object"],
        )

    def test_mixin_journal_seul(self):
        class Service(JournalisationMixin):
            pass
        sortie = capturer(Service().journaliser, "bonjour")
        self.assertIn("bonjour", sortie)

    def test_mixin_validation_seul(self):
        class Livre(ValidationMixin):
            def __init__(self, titre):
                self.titre = titre
        Livre("OK")
        with self.assertRaises(ValueError):
            Livre("")

    def test_mixin_historique_seul(self):
        class Note(HistoriqueMixin):
            def __init__(self):
                self._init_historique()
        n = Note()
        n.enregistrer_version("a")
        self.assertEqual(n.historique[0][1], "a")

    def test_historique_clone_les_valeurs_mutables(self):
        # Le mixin sert aussi pour des valeurs modifiables (listes) :
        # deepcopy évite que l'historique change avec l'original.
        class Note(HistoriqueMixin):
            def __init__(self):
                self._init_historique()
        n = Note()
        contenu = ["a"]
        n.enregistrer_version(contenu)
        contenu.append("b")  # on modifie l'original
        self.assertEqual(n.historique[0][1], ["a"])  # l'historique n'a pas changé


if __name__ == "__main__":
    unittest.main()