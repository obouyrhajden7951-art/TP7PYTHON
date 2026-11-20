"""
test_document.py - Tests de document.py
Lancer avec :  python -m unittest test_document -v
"""

import io
import json
import re
import unittest
from contextlib import redirect_stdout

from document import (
    Document, Horodatable, Validable, Serializable, Historisable,
)


def capturer(fonction, *args):
    """Exécute fonction(*args), retourne ce qu'elle a affiché avec print."""
    tampon = io.StringIO()
    with redirect_stdout(tampon):
        fonction(*args)
    return tampon.getvalue()


class TestSauvegarde(unittest.TestCase):
    def test_sortie_complete(self):
        doc = Document("Rapport", "Contenu important")
        lignes = capturer(doc.sauvegarder).splitlines()
        self.assertEqual(len(lignes), 3)
        # Ligne 1 : [LOG] Action à AAAA-MM-JJ HH:MM:SS.xxxxxx
        self.assertRegex(lignes[0], r"^\[LOG\] Action à \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
        self.assertEqual(lignes[1], "Validation OK")
        self.assertEqual(lignes[2], "Document 'Rapport' sauvegardé.")

    def test_titre_invalide_leve_erreur(self):
        for titre in ("", "   ", None, 123):
            with self.subTest(titre=titre):
                doc = Document(titre, "x")
                with redirect_stdout(io.StringIO()):
                    with self.assertRaises(ValueError) as ctx:
                        doc.sauvegarder()
                self.assertIn("Titre manquant", str(ctx.exception))

    def test_echec_ne_sauvegarde_pas(self):
        doc = Document("", "x")
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            with self.assertRaises(ValueError):
                doc.sauvegarder()
        self.assertNotIn("sauvegardé", tampon.getvalue())
        self.assertEqual(doc.historique, ())  # aucune action enregistrée


class TestSerializable(unittest.TestCase):
    def test_to_json(self):
        doc = Document("Rapport", "Contenu important")
        self.assertEqual(
            json.loads(doc.to_json()),
            {"titre": "Rapport", "contenu": "Contenu important"},
        )

    def test_accents_conserves(self):
        self.assertIn("Détaillé", Document("Détaillé", "é").to_json())

    def test_historique_non_exporte(self):
        # L'historique contient des datetime : il ne doit pas être dans le JSON
        doc = Document("A", "B")
        with redirect_stdout(io.StringIO()):
            doc.sauvegarder()
        data = json.loads(doc.to_json())
        self.assertNotIn("historique", data)
        self.assertNotIn("_historique", data)


class TestHistorisable(unittest.TestCase):
    def test_historique_vide_au_depart(self):
        self.assertEqual(Document("A", "B").historique, ())

    def test_actions_enregistrees_dans_l_ordre(self):
        doc = Document("A", "B")
        with redirect_stdout(io.StringIO()):
            doc.sauvegarder()
            doc.sauvegarder()
        self.assertEqual([a for _, a in doc.historique], ["sauvegarde", "sauvegarde"])

    def test_historique_en_lecture_seule(self):
        doc = Document("A", "B")
        with self.assertRaises(AttributeError):
            doc.historique.append(1)
        with self.assertRaises(AttributeError):
            doc.historique = []

    def test_historiques_separes_entre_objets(self):
        # Piège classique : une liste partagée par toutes les instances
        d1, d2 = Document("A", "B"), Document("C", "D")
        d1.enregistrer_action("x")
        self.assertEqual(d2.historique, ())


class TestAbstrait(unittest.TestCase):
    def test_validable_non_instanciable(self):
        with self.assertRaises(TypeError):
            Validable()

    def test_methode_abstraite_obligatoire(self):
        class Incomplet(Validable):
            pass  # n'implémente pas erreurs_validation
        with self.assertRaises(TypeError):
            Incomplet()

    def test_classe_complete_instanciable(self):
        class Complet(Validable):
            def erreurs_validation(self):
                return []
        with redirect_stdout(io.StringIO()):
            Complet().valider()

    def test_plusieurs_erreurs_regroupees(self):
        class Strict(Validable):
            def erreurs_validation(self):
                return ["erreur 1", "erreur 2"]
        with self.assertRaises(ValueError) as ctx:
            Strict().valider()
        self.assertEqual(str(ctx.exception), "erreur 1; erreur 2")


class TestStructure(unittest.TestCase):
    def test_mixins_utilisables_seuls(self):
        class Service(Horodatable):
            pass
        self.assertIn("[LOG]", capturer(Service().horodatage))

    def test_mro(self):
        noms = [c.__name__ for c in Document.__mro__]
        self.assertEqual(
            noms,
            ["Document", "Horodatable", "Validable", "ABC",
             "Serializable", "Historisable", "object"],
        )

    def test_document_est_instance_de_chaque_mixin(self):
        doc = Document("A", "B")
        for mixin in (Horodatable, Validable, Serializable, Historisable):
            self.assertIsInstance(doc, mixin)


if __name__ == "__main__":
    unittest.main()