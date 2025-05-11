CATEGORY_MAP = {
    "Céréales": ["Blé","Riz","Maïs","Orge","Avoine","Sorgho"],
    "Légumineuses et oléagineux": ["Soja","Haricots","Pois","Arachides","Tournesol","Colza"],
    "Fruits": ["Pommes","Bananes","Agrumes","Mangues","Raisins"],
    "Légumes": ["Tomates","Carottes","Oignons","Choux","Laitues"],
    "Tubercules et racines": ["Pommes de terre","Manioc","Ignames","Patates douces"],
    "Cultures industrielles": ["Coton","Canne à sucre","Tabac","Café","Cacao","Thé","Caoutchouc"],
}
ALL_CATEGORIES = set(CATEGORY_MAP.keys())
UNIT_CHOICES = [('kg','Kilogramme'),('g','Gramme'),('l','Litre')]
