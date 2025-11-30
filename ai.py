# ai_nutrition_consultant_ua.py
# Оновлений: фото замінено на AI-генерацію за точним описом (щоб уникнути помилок).
from __future__ import annotations
import json
import random
import datetime
import csv
import io
import os
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

try:
    from flask import Flask, request, render_template_string, jsonify, send_file, make_response
    FLASK_AVAILABLE = True
except Exception:
    FLASK_AVAILABLE = False

# ----------------------------
# Data models
# ----------------------------
@dataclass
class Nutrition:
    calories: float
    protein: float
    carbs: float
    fats: float

    def __add__(self, other: 'Nutrition') -> 'Nutrition':
        return Nutrition(
            self.calories + other.calories,
            self.protein + other.protein,
            self.carbs + other.carbs,
            self.fats + other.fats,
        )

    def to_dict(self):
        return asdict(self)


@dataclass
class Recipe:
    id: str
    name_uk: str
    tags: List[str]
    ingredients: Dict[str, float]
    nutrition: Nutrition
    steps_uk: List[str]
    image: str
    rating: float = 0.0
    votes: int = 0

    def matches(self, mood: str, goal: str) -> int:
        score = 0
        m = mood.lower()
        g = goal.lower()
        tag_lowers = [t.lower() for t in self.tags]
        for lt in tag_lowers:
            if lt in m:
                score += 3
            if lt in g:
                score += 4
        if 'light' in tag_lowers and 'lose' in g:
            score += 2
        if 'hearty' in tag_lowers and ('gain' in g or 'muscle' in g):
            score += 2
        return score

    def contains_forbidden(self, forbidden: List[str]) -> bool:
        """Return True if any forbidden term appears in ingredient names."""
        if not forbidden:
            return False
        lower_keys = ' '.join(self.ingredients.keys()).lower()
        for f in forbidden:
            if f.strip() == '':
                continue
            if f.lower() in lower_keys:
                return True
        return False

    def add_rating(self, value: float):
        try:
            total = self.rating * self.votes
            self.votes += 1
            total += float(value)
            self.rating = total / self.votes
        except Exception:
            pass


# ----------------------------
# Recipe storage & load
# ----------------------------
RECIPES: List[Recipe] = []

def load_sample_recipes():
    global RECIPES
    if RECIPES:
        return
    
    # Використовуємо pollination.ai для точної генерації страв.
    # seed додається для стабільності картинки (щоб не змінювалась при оновленні).
    base_img_url = "https://image.pollinations.ai/prompt/delicious%20food%20photorealistic%20"

    RECIPES = [
        # --- ORIGINAL RECIPES (20) ---
        Recipe('r001', 'Йогурт з ягодами і гранолою', ['breakfast', 'light', 'sweet'],
               {'йогурт грецький (200г)': 200, 'ягоди (100г)': 100, 'гранола (30г)': 30, 'мед (10г)': 10},
               Nutrition(330, 20, 35, 10),
               [
                   'Покласти йогурт у миску.',
                   'Промити та підсушити ягоди, додати зверху.',
                   'Посипати гранолою, полити медом.',
                   'Злегка перемішати і подати.'
               ],
               image=base_img_url + 'greek%20yogurt%20bowl%20with%20fresh%20berries%20and%20granola?width=400&height=300&nologo=true&seed=1'),
        Recipe('r002', 'Омлет з овочами', ['breakfast', 'high-protein'],
               {'яйця (2 шт)': 2, 'кабачок (80г)': 80, 'помідор (50г)': 50, 'олія (5мл)': 5},
               Nutrition(300, 18, 6, 20),
               [
                   'Натерти кабачок, віджати вологу.',
                   'Збити яйця, додати кабачок та дрібно порізаний помідор.',
                   'Посмажити на невеликій кількості олії до готовності.'
               ],
               image=base_img_url + 'omelet%20with%20zucchini%20and%20tomatoes?width=400&height=300&nologo=true&seed=2'),
        Recipe('r003', 'Авокадо-тост з яйцем', ['breakfast', 'light'],
               {'авокадо (1/2)': 0.5, 'хліб цільнозерновий (1 слайс)': 1, 'яйце (1 шт)': 1},
               Nutrition(310, 13, 26, 18),
               [
                   'Підсмажити хліб.',
                   'Розім\'яти авокадо з лимонним соком і сіллю.',
                   'Покласти авокадо на тост, додати яйце пашот зверху.'
               ],
               image=base_img_url + 'avocado%20toast%20with%20poached%20egg?width=400&height=300&nologo=true&seed=3'),
        # --- bowls / smoothie / drinks / snacks / sweet
        Recipe('r010', 'Смузі боул з манго', ['breakfast', 'sweet', 'drink'],
               {'манго (150г)': 150, 'банан (50г)': 50, 'йогурт (120г)': 120, 'горіхи (10г)': 10},
               Nutrition(350, 8, 60, 8),
               [
                   'Збити манго, банан і йогурт до кремової текстури.',
                   'Викласти у миску, прикрасити горіхами та насінням.'
               ],
               image=base_img_url + 'mango%20smoothie%20bowl%20yellow?width=400&height=300&nologo=true&seed=10'),
        Recipe('r011', 'Какао з мигдальним молоком', ['drink', 'sweet'],
               {'мигдальне молоко (200мл)': 200, 'какао-порошок (10г)': 10, 'мед (10г)': 10},
               Nutrition(200, 4, 28, 8),
               [
                   'Нагріти молоко, додати какао і мед, ретельно збити.',
                   'Подавати гарячим.'
               ],
               image=base_img_url + 'hot%20cocoa%20drink%20in%20mug?width=400&height=300&nologo=true&seed=11'),
        Recipe('r012', 'Протеїновий шейк', ['drink', 'high-protein'],
               {'протеїн (30г)': 30, 'молоко/вода (250мл)': 250, 'банан (50г)': 50},
               Nutrition(320, 28, 30, 6),
               [
                   'Змішати інгредієнти у шейкері або блендері.',
                   'Пити відразу після приготування.'
               ],
               image=base_img_url + 'protein%20shake%20in%20glass%20with%20banana?width=400&height=300&nologo=true&seed=12'),
        # --- lunch/dinner
        Recipe('r020', 'Куряче філе з овочами', ['lunch', 'balanced'],
               {'куряче філе (150г)': 150, 'броколі (120г)': 120, 'морква (80г)': 80, 'олія (10мл)': 10},
               Nutrition(420, 38, 20, 18),
               [
                   'Порізати філе на шматки, посолити.',
                   'Обсмажити на олії до золотистої скоринки.',
                   'Додати овочі, накрити і тушкувати 8-10 хв.'
               ],
               image=base_img_url + 'fried%20chicken%20breast%20fillet%20with%20broccoli%20and%20carrots?width=400&height=300&nologo=true&seed=20'),
        Recipe('r021', 'Сьомга з лимоном і кіноа', ['dinner', 'high-protein'],
               {'сьомга (150г)': 150, 'кіноа (80г)': 80, 'лимон (30г)': 30},
               Nutrition(560, 36, 48, 24),
               [
                   'Замаринувати сьомгу у лимонному соці, сіль, перець.',
                   'Запекти 12-15 хв при 180°C.',
                   'Паралельно зварити кіноа, подати разом.'
               ],
               image=base_img_url + 'baked%20salmon%20steak%20with%20quinoa%20and%20lemon?width=400&height=300&nologo=true&seed=21'),
        # --- snacks
        Recipe('r030', 'Хумус з овочами', ['snack', 'vegetarian'],
               {'нут відварний (150г)': 150, 'тахіні (15г)': 15, 'олія (10мл)': 10, 'овочі (100г)': 100},
               Nutrition(240, 8, 30, 10),
               [
                   'Змішати нут з тахіні, олією і лимоном в блендері до однорідності.',
                   'Подавати з нарізаними овочами.'
               ],
               image=base_img_url + 'hummus%20bowl%20with%20carrot%20sticks?width=400&height=300&nologo=true&seed=30'),
        # --- more items
        Recipe('r040', 'Паста карбонара (полегшена)', ['lunch', 'comfort'],
               {'спагеті (80г)': 80, 'бекон (30г)': 30, 'яйце (1 шт)': 1, 'пармезан (20г)': 20},
               Nutrition(520, 22, 61, 20),
               [
                   'Зварити пасту до al dente.',
                   'Обсмажити бекон до хрусткого стану.',
                   'Змішати пасту з яйцем та сиром швидко, поки яйце не згорнулося.'
               ],
               image=base_img_url + 'pasta%20carbonara%20spaghetti?width=400&height=300&nologo=true&seed=40'),
        Recipe('r041', 'Панкейки на кефірі', ['breakfast', 'sweet'],
               {'борошно (100г)': 100, 'кефір (150мл)': 150, 'яйце (1 шт)': 1},
               Nutrition(420, 10, 60, 12),
               [
                   'Змішати інгредієнти до гладкого тіста.',
                   'Смажити на сковороді до золотистого кольору.'
               ],
               image=base_img_url + 'fluffy%20pancakes%20stack?width=400&height=300&nologo=true&seed=41'),
        Recipe('r042', 'Суп-пюре з гарбуза', ['lunch', 'vegetarian', 'light'],
               {'гарбуз (400г)': 400, 'цибуля (50г)': 50, 'вода (500мл)': 500},
               Nutrition(180, 3, 30, 6),
               [
                   'Обсмажити цибулю, додати гарбуз і воду, варити до м\'якості.',
                   'Пропюрирувати блендером і додати спеції.'
               ],
               image=base_img_url + 'pumpkin%20cream%20soup%20orange?width=400&height=300&nologo=true&seed=42'),
        Recipe('r043', 'Кесаділья з куркою', ['lunch', 'comfort'],
               {'тортилья (1 шт)': 1, 'курка (80г)': 80, 'сир (60г)': 60},
               Nutrition(560, 32, 40, 28),
               [
                   'Обсмажити курку з приправами, покласти на тортилью з сиром.',
                   'Скласти і обсмажити до рум\'янцю.'
               ],
               image=base_img_url + 'chicken%20quesadilla%20mexican?width=400&height=300&nologo=true&seed=43'),
        Recipe('r044', 'Запечені яблука з медом', ['dessert', 'sweet'],
               {'яблука (2 шт)': 2, 'мед (20г)': 20, 'горіхи (20г)': 20},
               Nutrition(280, 4, 48, 8),
               [
                   'Вирізати серцевину яблук, заповнити медом і горіхами.',
                   'Запікати 20-25 хв при 180°C.'
               ],
               image=base_img_url + 'baked%20apples%20with%20honey%20and%20nuts?width=400&height=300&nologo=true&seed=44'),
        Recipe('r045', 'Теплий шоколадний напій', ['drink', 'sweet'],
               {'молоко (200мл)': 200, 'какао (15г)': 15, 'цукор (10г)': 10},
               Nutrition(260, 8, 28, 12),
               [
                   'Підігріти молоко, додати какао, добре розмішати.',
                   'Подати гарячим з невеликою кількістю збитих вершків за бажанням.'
               ],
               image=base_img_url + 'hot%20chocolate%20drink?width=400&height=300&nologo=true&seed=45'),
        Recipe('r046', 'Запечена курка з картоплею', ['dinner', 'hearty'],
               {'курка (200г)': 200, 'картопля (200г)': 200, 'олія (10мл)': 10},
               Nutrition(740, 48, 60, 28),
               [
                   'Приправити курку, розкласти з картоплею на деко, запікати 40-50 хв при 180°C.'
               ],
               image=base_img_url + 'roasted%20chicken%20legs%20with%20potatoes?width=400&height=300&nologo=true&seed=46'),
        Recipe('r047', 'Боул з кіноа і овочами', ['lunch', 'bowl', 'vegetarian'],
               {'кіноа (80г)': 80, 'авокадо (1/2)': 0.5, 'овочі (120г)': 120},
               Nutrition(420, 12, 48, 18),
               [
                   'Зварити кіноа, змішати з овочами та авокадо, заправити соусом.'
               ],
               image=base_img_url + 'quinoa%20bowl%20avocado%20vegetables?width=400&height=300&nologo=true&seed=47'),
        Recipe('r048', 'Енергетичний батончик домашній', ['snack', 'sweet'],
               {'горіхи (50г)': 50, 'фініки (100г)': 100, 'вівсянка (40г)': 40},
               Nutrition(320, 8, 40, 14),
               [
                   'Подрібнити інгредієнти в блендері, сформувати батончики, охолодити.'
               ],
               image=base_img_url + 'granola%20energy%20bar%20nuts%20dates?width=400&height=300&nologo=true&seed=48'),
        Recipe('r049', 'Том-ям (легкий)', ['dinner', 'light'],
               {'креветки (120г)': 120, 'бульйон (400мл)': 400, 'лимон (20г)': 20},
               Nutrition(220, 18, 10, 8),
               [
                   'Закип\'ятити бульйон, додати креветки та спеції, довести до готовності.'
               ],
               image=base_img_url + 'tom%20yam%20soup%20shrimp?width=400&height=300&nologo=true&seed=49'),
        Recipe('r050', 'Крем-брюле (полегшений)', ['dessert', 'sweet'],
               {'жовтки (2 шт)': 2, 'молоко (200мл)': 200, 'цукор (15г)': 15},
               Nutrition(380, 8, 38, 22),
               [
                   'Змішати жовтки з молоком і цукром, випікати на водяній бані 30 хв при 150°C.'
               ],
               image=base_img_url + 'creme%20brulee%20dessert?width=400&height=300&nologo=true&seed=50'),

        # --- NEW RECIPES (50) ---
        # 1. New Breakfast Recipes
        Recipe('r051', 'Вівсянка на воді з яблуком і корицею', ['breakfast', 'light', 'vegetarian'],
               {'вівсяні пластівці (50г)': 50, 'вода (200мл)': 200, 'яблуко (100г)': 100, 'кориця': 1},
               Nutrition(280, 8, 45, 6),
               [
                   'Зварити вівсянку на воді до готовності.',
                   'Додати нарізане кубиками яблуко і посипати корицею.'
               ],
               image=base_img_url + 'oatmeal%20porridge%20with%20apple%20and%20cinnamon?width=400&height=300&nologo=true&seed=51'),
        Recipe('r052', 'Сирники запечені з родзинками', ['breakfast', 'sweet', 'high-protein'],
               {'сир кисломолочний (200г)': 200, 'яйце (1 шт)': 1, 'борошно (10г)': 10, 'родзинки (10г)': 10},
               Nutrition(340, 25, 30, 12),
               [
                   'Змішати сир, яйце, борошно та родзинки.',
                   'Сформувати сирники, запекти в духовці при 180°C близько 20 хв.'
               ],
               image=base_img_url + 'ukrainian%20syrniki%20cottage%20cheese%20pancakes%20raisins?width=400&height=300&nologo=true&seed=52'),
        Recipe('r053', 'Яєчня з грибами та шпинатом', ['breakfast', 'high-protein'],
               {'яйця (3 шт)': 3, 'печериці (100г)': 100, 'шпинат (50г)': 50, 'олія (5мл)': 5},
               Nutrition(310, 20, 5, 23),
               [
                   'Обсмажити на сковороді гриби та шпинат.',
                   'Додати збиті яйця, готувати до готовності.'
               ],
               image=base_img_url + 'scrambled%20eggs%20with%20spinach%20and%20mushrooms?width=400&height=300&nologo=true&seed=53'),
        Recipe('r054', 'Тост з арахісовою пастою та бананом', ['breakfast', 'hearty', 'sweet'],
               {'хліб цільнозерновий (2 слайси)': 2, 'арахісова паста (30г)': 30, 'банан (50г)': 50},
               Nutrition(380, 14, 35, 20),
               [
                   'Підсмажити хліб.',
                   'Намазати арахісову пасту, покласти кружальця банана.'
               ],
               image=base_img_url + 'toast%20with%20peanut%20butter%20and%20banana%20slices?width=400&height=300&nologo=true&seed=54'),
        Recipe('r055', 'Чиа пудинг на кокосовому молоці', ['breakfast', 'light', 'drink'],
               {'насіння чіа (30г)': 30, 'кокосове молоко (200мл)': 200, 'мед (10г)': 10, 'ягоди (30г)': 30},
               Nutrition(320, 10, 38, 15),
               [
                   'Змішати чіа, молоко та мед. Залишити на ніч у холодильнику.',
                   'Вранці додати свіжі ягоди.'
               ],
               image=base_img_url + 'chia%20pudding%20glass%20berries?width=400&height=300&nologo=true&seed=55'),
        Recipe('r056', 'Боул з гречки та свіжих овочів', ['breakfast', 'vegetarian', 'balanced'],
               {'гречка відварна (150г)': 150, 'огірок (50г)': 50, 'помідор (50г)': 50, 'зелень': 5},
               Nutrition(360, 10, 60, 8),
               [
                   'Змішати теплу гречку з нарізаними овочами.',
                   'Заправити невеликою кількістю олії та зеленню.'
               ],
               image=base_img_url + 'buckwheat%20porridge%20bowl%20with%20cucumber%20and%20tomato?width=400&height=300&nologo=true&seed=56'),
        Recipe('r057', 'Фріттата з куркою і сиром', ['breakfast', 'high-protein', 'hearty'],
               {'яйця (3 шт)': 3, 'куряче філе відварне (50г)': 50, 'сир твердий (30г)': 30, 'молоко (30мл)': 30},
               Nutrition(410, 35, 8, 25),
               [
                   'Змішати збиті яйця, молоко, нарізану курку та натертий сир.',
                   'Запекти в невеликій формі до готовності.'
               ],
               image=base_img_url + 'baked%20frittata%20egg%20casserole?width=400&height=300&nologo=true&seed=57'),
        Recipe('r058', 'Шоколадна вівсянка (за ніч)', ['breakfast', 'sweet'],
               {'вівсяні пластівці (50г)': 50, 'молоко (150мл)': 150, 'какао (5г)': 5, 'банан (50г)': 50},
               Nutrition(350, 12, 50, 12),
               [
                   'Змішати пластівці, молоко та какао. Поставити на ніч у холодильник.',
                   'Вранці додати нарізаний банан.'
               ],
               image=base_img_url + 'chocolate%20overnight%20oats%20jar?width=400&height=300&nologo=true&seed=58'),
        Recipe('r059', 'Вафлі зі шпинатом та лососем', ['breakfast', 'light', 'high-protein'],
               {'борошно (50г)': 50, 'молоко (100мл)': 100, 'шпинат (50г)': 50, 'лосось слабосолений (30г)': 30},
               Nutrition(390, 28, 35, 16),
               [
                   'Приготувати тісто, додавши шпинат. Випекти вафлі.',
                   'Подавати зі шматочками лосося.'
               ],
               image=base_img_url + 'green%20spinach%20waffles%20with%20salmon?width=400&height=300&nologo=true&seed=59'),
        Recipe('r060', 'Сендвіч з індичкою та авокадо', ['breakfast', 'balanced'],
               {'хліб (2 слайси)': 2, 'філе індички (50г)': 50, 'авокадо (30г)': 30, 'салат': 1},
               Nutrition(370, 25, 30, 17),
               [
                   'Підсмажити хліб. Зібрати сендвіч з авокадо, індичкою та салатом.'
               ],
               image=base_img_url + 'turkey%20avocado%20sandwich?width=400&height=300&nologo=true&seed=60'),
        Recipe('r061', 'Протеїновий пудинг з кави', ['breakfast', 'drink', 'high-protein'],
               {'протеїн кавовий (30г)': 30, 'вода/молоко (200мл)': 200, 'лід': 1},
               Nutrition(220, 25, 15, 6),
               [
                   'Змішати всі інгредієнти у шейкері або блендері.',
                   'Подавати холодним з льодом.'
               ],
               image=base_img_url + 'iced%20coffee%20protein%20shake?width=400&height=300&nologo=true&seed=61'),
        Recipe('r062', 'Рисова каша на молоці з корицею', ['breakfast', 'sweet', 'comfort'],
               {'рис (60г)': 60, 'молоко (250мл)': 250, 'цукор (10г)': 10, 'кориця': 1},
               Nutrition(360, 10, 65, 7),
               [
                   'Зварити рис на молоці до готовності.',
                   'Додати цукор і корицю за смаком, перемішати.'
               ],
               image=base_img_url + 'rice%20pudding%20with%20cinnamon?width=400&height=300&nologo=true&seed=62'),
        Recipe('r063', 'Омлет у лаваші з сиром', ['breakfast', 'hearty'],
               {'лаваш тонкий (50г)': 50, 'яйця (2 шт)': 2, 'сир твердий (30г)': 30},
               Nutrition(380, 22, 30, 20),
               [
                   'Приготувати омлет.',
                   'Загорнути омлет та натертий сир у лаваш і прогріти на сковороді.'
               ],
               image=base_img_url + 'omelet%20cheese%20wrap%20lavash?width=400&height=300&nologo=true&seed=63'),
        Recipe('r064', 'Фруктовий салат з йогуртом', ['breakfast', 'light', 'sweet'],
               {'йогурт натуральний (150г)': 150, 'банан (50г)': 50, 'ківі (50г)': 50, 'апельсин (50г)': 50},
               Nutrition(290, 10, 45, 8),
               [
                   'Нарізати фрукти.',
                   'Змішати з йогуртом.'
               ],
               image=base_img_url + 'fruit%20salad%20bowl%20yogurt?width=400&height=300&nologo=true&seed=64'),
        Recipe('r065', 'Гречана каша з кефіром (за ніч)', ['breakfast', 'light', 'balanced'],
               {'гречка (50г)': 50, 'кефір (200мл)': 200, 'насіння льону (5г)': 5},
               Nutrition(270, 12, 40, 7),
               [
                   'Залити гречку кефіром на ніч.',
                   'Додати насіння льону перед вживанням.'
               ],
               image=base_img_url + 'buckwheat%20with%20kefir%20healthy?width=400&height=300&nologo=true&seed=65'),

        # 2. New Lunch Recipes
        Recipe('r066', 'Сочевиця з овочами та тофу', ['lunch', 'vegetarian', 'balanced'],
               {'сочевиця відварна (150г)': 150, 'тофу (80г)': 80, 'морква (50г)': 50, 'цибуля (50г)': 50},
               Nutrition(450, 25, 55, 15),
               [
                   'Обсмажити овочі, додати сочевицю та нарізаний тофу.',
                   'Тушкувати 10 хв, додати спеції.'
               ],
               image=base_img_url + 'lentils%20stew%20with%20tofu%20vegetables?width=400&height=300&nologo=true&seed=66'),
        Recipe('r067', 'Кус-кус з тунцем та огірком', ['lunch', 'light', 'high-protein'],
               {'kus-kus (60g)': 60, 'тунець консервований (100г)': 100, 'огірок (80г)': 80, 'олія (5мл)': 5},
               Nutrition(410, 30, 45, 12),
               [
                   'Запарити кус-кус.',
                   'Змішати з тунцем, нарізаним огірком та олією.'
               ],
               image=base_img_url + 'couscous%20salad%20with%20tuna?width=400&height=300&nologo=true&seed=67'),
        Recipe('r068', 'Салат Цезар (полегшений)', ['lunch', 'high-protein', 'light'],
               {'куряче філе (100г)': 100, 'салат ромен': 50, 'помідори чері (50г)': 50, 'соус Цезар (20г)': 20},
               Nutrition(390, 30, 15, 22),
               [
                   'Нарізати овочі, додати нарізану запечену курку.',
                   'Заправити легким соусом Цезар.'
               ],
               image=base_img_url + 'caesar%20salad%20chicken?width=400&height=300&nologo=true&seed=68'),
        Recipe('r069', 'Овочевий суп-пюре з броколі', ['lunch', 'light', 'vegetarian'],
               {'броколі (150г)': 150, 'картопля (50г)': 50, 'цибуля (30г)': 30, 'хліб для грінок (30г)': 30},
               Nutrition(250, 8, 35, 8),
               [
                   'Зварити овочі до м\'якості.',
                   'Пюрувати блендером, подати з підсушеними грінками.'
               ],
               image=base_img_url + 'green%20broccoli%20cream%20soup?width=400&height=300&nologo=true&seed=69'),
        Recipe('r070', 'Плов з куркою та морквою', ['lunch', 'hearty', 'balanced'],
               {'рис (100г)': 100, 'курка (100г)': 100, 'морква (80г)': 80, 'олія (15мл)': 15},
               Nutrition(620, 35, 80, 20),
               [
                   'Обсмажити курку та овочі. Додати рис та воду.',
                   'Готувати під кришкою до готовності рису.'
               ],
               image=base_img_url + 'pilaf%20rice%20chicken%20carrot?width=400&height=300&nologo=true&seed=70'),
        Recipe('r071', 'Буріто боул з яловичиною', ['lunch', 'high-protein', 'comfort'],
               {'яловичина відварна (100г)': 100, 'рис (80г)': 80, 'квасоля (50г)': 50, 'кукурудза (30г)': 30},
               Nutrition(550, 40, 50, 20),
               [
                   'Змішати всі інгредієнти в мисці.',
                   'Заправити легким соусом або олією та спеціями.'
               ],
               image=base_img_url + 'burrito%20bowl%20beef%20beans%20corn?width=400&height=300&nologo=true&seed=71'),
        Recipe('r072', 'Паста з томатним соусом та базиліком', ['lunch', 'comfort', 'vegetarian'],
               {'спагеті (100г)': 100, 'томати протерті (150г)': 150, 'базилік': 5, 'олія (5мл)': 5},
               Nutrition(480, 15, 80, 10),
               [
                   'Зварити пасту до стану al dente.',
                   'Змішати з гарячим томатним соусом та свіжим базиліком.'
               ],
               image=base_img_url + 'spaghetti%20pasta%20tomato%20sauce%20basil?width=400&height=300&nologo=true&seed=72'),
        Recipe('r073', 'Деруни з нежирною сметаною', ['lunch', 'comfort', 'hearty'],
               {'картопля (200г)': 200, 'яйце (1 шт)': 1, 'борошно (10г)': 10, 'сметана (50г)': 50},
               Nutrition(510, 10, 60, 25),
               [
                   'Натерти картоплю, змішати з яйцем та борошном.',
                   'Посмажити деруни. Подати з нежирною сметаною.'
               ],
               image=base_img_url + 'potato%20pancakes%20sour%20cream?width=400&height=300&nologo=true&seed=73'),
        Recipe('r074', 'Капусняк з грибами', ['lunch', 'vegetarian', 'light'],
               {'квашена капуста (150г)': 150, 'гриби (80г)': 80, 'картопля (50г)': 50, 'вода (500мл)': 500},
               Nutrition(300, 10, 40, 10),
               [
                   'Зварити легкий суп з капусти, грибів та картоплі.',
                   'Подавати гарячим, можна додати зелень.'
               ],
               image=base_img_url + 'sauerkraut%20soup%20mushrooms?width=400&height=300&nologo=true&seed=74'),
        Recipe('r075', 'Теплий салат з кіноа та креветками', ['lunch', 'high-protein', 'light'],
               {'кіноа (60г)': 60, 'креветки (100г)': 100, 'авокадо (30г)': 30, 'рукола': 30},
               Nutrition(430, 35, 40, 15),
               [
                   'Зварити кіноа, обсмажити креветки.',
                   'Змішати теплу кіноа, креветки, нарізане авокадо та руколу.'
               ],
               image=base_img_url + 'quinoa%20salad%20shrimp%20avocado?width=400&height=300&nologo=true&seed=75'),
        Recipe('r076', 'Котлети з індички з овочевим пюре', ['lunch', 'high-protein', 'balanced'],
               {'фарш індички (120г)': 120, 'картопля (100г)': 100, 'броколі (50г)': 50, 'морква (50г)': 50},
               Nutrition(490, 40, 45, 18),
               [
                   'Приготувати котлети з фаршу на пару або запекти.',
                   'Зробити пюре з картоплі, броколі та моркви.'
               ],
               image=base_img_url + 'turkey%20meatballs%20mashed%20potatoes?width=400&height=300&nologo=true&seed=76'),
        Recipe('r077', 'Булгур з куркою та соусом теріякі', ['lunch', 'comfort', 'balanced'],
               {'булгур (80г)': 80, 'курка (100г)': 100, 'соус теріякі (20г)': 20, 'перець болгарський (50г)': 50},
               Nutrition(560, 38, 65, 18),
               [
                   'Відварити булгур.',
                   'Обсмажити курку з перцем і соусом теріякі. Змішати з булгуром.'
               ],
               image=base_img_url + 'bulgur%20chicken%20teriyaki?width=400&height=300&nologo=true&seed=77'),
        Recipe('r078', 'Суп Мінестроне', ['lunch', 'light', 'vegetarian'],
               {'квасоля (50г)': 50, 'макарони дрібні (30г)': 30, 'томати (100г)': 100, 'кабачок (50г)': 50, 'бульйон': 400},
               Nutrition(280, 8, 45, 8),
               [
                   'Зварити овочі та квасолю у бульйоні, додати дрібні макарони.',
                   'Подавати зі свіжим базиліком.'
               ],
               image=base_img_url + 'minestrone%20soup%20vegetables?width=400&height=300&nologo=true&seed=78'),
        Recipe('r079', 'Запечена риба (тріска) з травами', ['lunch', 'high-protein', 'light'],
               {'тріска філе (150г)': 150, 'трави, лимон': 10, 'олія (10мл)': 10},
               Nutrition(380, 35, 10, 22),
               [
                   'Запекти філе тріски з лимоном та травами 15 хв при 180°C.'
               ],
               image=base_img_url + 'baked%20cod%20fish%20lemon%20herbs?width=400&height=300&nologo=true&seed=79'),
        Recipe('r080', 'Міні-піца на цільнозерновому тісті', ['lunch', 'comfort', 'balanced'],
               {'тісто цільнозернове (100г)': 100, 'томатний соус (30г)': 30, 'сир моцарела (50г)': 50, 'печериці (30г)': 30},
               Nutrition(520, 25, 60, 20),
               [
                   'Сформувати міні-піцу. Додати соус, сир та печериці.',
                   'Запекти до рум\'янцю.'
               ],
               image=base_img_url + 'mini%20pizza%20mushrooms?width=400&height=300&nologo=true&seed=80'),

        # 3. New Dinner Recipes
        Recipe('r081', 'Гречка з курячими сердечками', ['dinner', 'hearty', 'high-protein'],
               {'гречка (80г)': 80, 'курячі сердечка (120г)': 120, 'цибуля (30г)': 30, 'сметана нежирна (20г)': 20},
               Nutrition(480, 35, 45, 18),
               [
                   'Відварити гречку.',
                   'Сердечка потушкувати з цибулею та нежирною сметаною.'
               ],
               image=base_img_url + 'buckwheat%20porridge%20stewed%20chicken%20hearts?width=400&height=300&nologo=true&seed=81'),
        Recipe('r082', 'Запечений батат з сиром фета', ['dinner', 'vegetarian', 'balanced'],
               {'батат (200г)': 200, 'сир фета (30г)': 30, 'олія (5мл)': 5, 'спеції': 5},
               Nutrition(410, 12, 55, 16),
               [
                   'Нарізати батат, запекти до м\'якості.',
                   'Посипати сиром фета та спеціями.'
               ],
               image=base_img_url + 'baked%20sweet%20potato%20feta%20cheese?width=400&height=300&nologo=true&seed=82'),
        Recipe('r083', 'Хек тушкований з овочами', ['dinner', 'high-protein', 'light'],
               {'хек філе (150г)': 150, 'морква (50г)': 50, 'помідори (50г)': 50, 'цибуля (30г)': 30},
               Nutrition(320, 30, 15, 14),
               [
                   'Нарізати овочі та тушкувати їх.',
                   'Додати філе хека і тушкувати до готовності риби.'
               ],
               image=base_img_url + 'stewed%20white%20fish%20vegetables?width=400&height=300&nologo=true&seed=83'),
        Recipe('r084', 'Рататуй з яйцем пашот', ['dinner', 'light', 'vegetarian'],
               {'кабачок (100г)': 100, 'баклажан (100г)': 100, 'томати (100г)': 100, 'яйце (1 шт)': 1},
               Nutrition(300, 15, 25, 15),
               [
                   'Нарізати та запекти овочі.',
                   'Подати з яйцем пашот зверху.'
               ],
               image=base_img_url + 'ratatouille%20vegetables%20poached%20egg?width=400&height=300&nologo=true&seed=84'),
        Recipe('r085', 'Стейк з індички з зеленим салатом', ['dinner', 'high-protein', 'light'],
               {'стейк індички (150г)': 150, 'салат зелений (100г)': 100, 'олія для салату (10мл)': 10},
               Nutrition(420, 45, 10, 22),
               [
                   'Обсмажити або запекти стейк індички.',
                   'Подати з легким зеленим салатом, заправленим олією.'
               ],
               image=base_img_url + 'turkey%20steak%20green%20salad?width=400&height=300&nologo=true&seed=85'),
        Recipe('r086', 'Запіканка з макаронів та сиру', ['dinner', 'comfort', 'hearty'],
               {'макарони (100г)': 100, 'сир твердий (50г)': 50, 'молоко (50мл)': 50, 'яйце (1 шт)': 1},
               Nutrition(580, 30, 65, 25),
               [
                   'Зварити макарони. Змішати з сиром, яйцем та молоком.',
                   'Запекти в духовці до золотистої скоринки.'
               ],
               image=base_img_url + 'macaroni%20cheese%20casserole?width=400&height=300&nologo=true&seed=86'),
        Recipe('r087', 'Форель запечена з броколі', ['dinner', 'high-protein', 'balanced'],
               {'форель філе (120г)': 120, 'броколі (150г)': 150, 'олія (10мл)': 10},
               Nutrition(490, 38, 20, 28),
               [
                   'Запекти філе форелі та броколі разом при 180°C 15-20 хв.'
               ],
               image=base_img_url + 'baked%20trout%20fish%20broccoli?width=400&height=300&nologo=true&seed=87'),
        Recipe('r088', 'Овочеве карі з нутом', ['dinner', 'vegetarian', 'comfort'],
               {'нут консервований (100г)': 100, 'кокосове молоко (100мл)': 100, 'каррі паста (10г)': 10, 'овочі мікс (100г)': 100},
               Nutrition(450, 15, 60, 18),
               [
                   'Тушкувати нут та овочі у кокосовому молоці з додаванням пасти каррі.'
               ],
               image=base_img_url + 'chickpea%20vegetable%20curry?width=400&height=300&nologo=true&seed=88'),
        Recipe('r089', 'Бургер з котлетою з червоної сочевиці', ['dinner', 'vegetarian', 'comfort'],
               {'булочка цільнозернова (70г)': 70, 'котлета сочевична (100г)': 100, 'сир (20г)': 20, 'салат': 10},
               Nutrition(540, 20, 60, 25),
               [
                   'Приготувати котлету. Скласти бургер з овочами та сиром.'
               ],
               image=base_img_url + 'vegetarian%20burger%20lentil%20patty?width=400&height=300&nologo=true&seed=89'),
        Recipe('r090', 'Картопляне пюре з курячими тефтелями', ['dinner', 'hearty', 'comfort'],
               {'картопля (200г)': 200, 'фарш курячий (100г)': 100, 'молоко (50мл)': 50, 'олія (10мл)': 10},
               Nutrition(600, 35, 60, 25),
               [
                   'Зробити тефтелі на пару або запекти.',
                   'Зварити картопляне пюре з молоком та олією.'
               ],
               image=base_img_url + 'mashed%20potatoes%20meatballs?width=400&height=300&nologo=true&seed=90'),
        Recipe('r091', 'Салат з квасолею та курячим філе', ['dinner', 'high-protein', 'balanced'],
               {'куряче філе (100г)': 100, 'квасоля консервована (100г)': 100, 'перець болгарський (50г)': 50, 'олія': 5},
               Nutrition(410, 40, 35, 14),
               [
                   'Змішати нарізане філе, квасолю та перець.',
                   'Заправити олією та спеціями.'
               ],
               image=base_img_url + 'chicken%20bean%20salad?width=400&height=300&nologo=true&seed=91'),
        Recipe('r092', 'Голубці ліниві', ['dinner', 'comfort', 'balanced'],
               {'фарш яловичий (100г)': 100, 'капуста (100г)': 100, 'рис (50г)': 50, 'томатний соус': 50},
               Nutrition(480, 30, 50, 20),
               [
                   'Змішати фарш, нарізану капусту та відварений рис.',
                   'Сформувати, потушкувати у томатному соусі.'
               ],
               image=base_img_url + 'cabbage%20rolls%20stew%20tomato?width=400&height=300&nologo=true&seed=92'),
        Recipe('r093', 'Овочі-гриль з хумусом', ['dinner', 'light', 'vegetarian'],
               {'кабачок (100г)': 100, 'перець (100г)': 100, 'хумус (50г)': 50, 'баклажан (50г)': 50},
               Nutrition(350, 10, 40, 18),
               [
                   'Нарізати овочі та обсмажити на грилі.',
                   'Подати з хумусом.'
               ],
               image=base_img_url + 'grilled%20vegetables%20hummus?width=400&height=300&nologo=true&seed=93'),
        Recipe('r094', 'Яловичина тушкована з чорносливом', ['dinner', 'hearty', 'high-protein'],
               {'яловичина (120г)': 120, 'чорнослив (30г)': 30, 'рис (70г)': 70},
               Nutrition(520, 40, 50, 20),
               [
                   'Тушкувати яловичину з чорносливом та спеціями.',
                   'Подати з відвареним рисом.'
               ],
               image=base_img_url + 'beef%20stew%20prunes%20rice?width=400&height=300&nologo=true&seed=94'),
        Recipe('r095', 'Крем-суп з гарбуза та імбиру', ['dinner', 'light', 'vegetarian'],
               {'гарбуз (300г)': 300, 'імбир (10г)': 10, 'бульйон овочевий (300мл)': 300},
               Nutrition(200, 5, 30, 5),
               [
                   'Зварити гарбуз з імбиром у бульйоні.',
                   'Пропюрувати блендером.'
               ],
               image=base_img_url + 'pumpkin%20ginger%20soup?width=400&height=300&nologo=true&seed=95'),

        # 4. New Snacks/Drinks/Desserts
        Recipe('r096', 'Фруктове морозиво (банан/ягоди)', ['dessert', 'sweet', 'light'],
               {'банан заморожений (100г)': 100, 'ягоди заморожені (50г)': 50, 'йогурт (20г)': 20},
               Nutrition(180, 3, 35, 3),
               [
                   'Збити всі заморожені інгредієнти у блендері до консистенції морозива.',
                   'Подавати негайно.'
               ],
               image=base_img_url + 'fruit%20ice%20cream%20sorbet%20berries?width=400&height=300&nologo=true&seed=96'),
        Recipe('r097', 'Овочеві палички з йогуртовим соусом', ['snack', 'light', 'vegetarian'],
               {'морква (50г)': 50, 'селера (50г)': 50, 'йогурт грецький (50г)': 50, 'спеції': 2},
               Nutrition(150, 8, 15, 6),
               [
                   'Нарізати моркву та селеру паличками.',
                   'Йогурт змішати зі спеціями для соусу.'
               ],
               image=base_img_url + 'vegetable%20sticks%20carrot%20celery%20dip?width=400&height=300&nologo=true&seed=97'),
        Recipe('r098', 'Протеїновий батончик без випікання', ['snack', 'high-protein', 'sweet'],
               {'протеїновий порошок (20г)': 20, 'вівсянка (30г)': 30, 'мед (15г)': 15, 'арахісова паста (10г)': 10},
               Nutrition(260, 15, 30, 10),
               [
                   'Змішати всі інгредієнти.',
                   'Сформувати батончики та охолодити у морозильній камері.'
               ],
               image=base_img_url + 'protein%20bar%20homemade?width=400&height=300&nologo=true&seed=98'),
        Recipe('r099', 'Чай масала з мигдальним молоком', ['drink', 'sweet', 'comfort'],
               {'мигдальне молоко (200мл)': 200, 'чай/спеції масала': 5, 'мед (10г)': 10},
               Nutrition(120, 3, 20, 3),
               [
                   'Підігріти молоко, додати чай/спеції масала та мед.',
                   'Настояти кілька хвилин, процідити.'
               ],
               image=base_img_url + 'masala%20chai%20tea%20spices?width=400&height=300&nologo=true&seed=99'),
        Recipe('r100', 'Горіхово-фруктова суміш', ['snack', 'hearty', 'sweet'],
               {'волоські горіхи (30г)': 30, 'родзинки (30г)': 30, 'курага (30г)': 30},
               Nutrition(350, 10, 35, 20),
               [
                   'Змішати горіхи, родзинки та курагу.',
                   'Зберігати у герметичному контейнері.'
               ],
               image=base_img_url + 'nuts%20dried%20fruits%20mix?width=400&height=300&nologo=true&seed=100'),
    ]


# ----------------------------
# Profile calculations and config
# ----------------------------
DEFAULT_PROFILE = {
    'age': 30,
    'sex': 'male',
    'weight_kg': 75.0,
    'height_cm': 175.0,
    'activity': 'moderate',
}

ACTIVITY_MULTIPLIERS = {
    'sedentary': 1.2,
    'office': 1.25,
    'student': 1.3,
    'light': 1.375,
    'moderate': 1.55,
    'daily-sport': 1.65,
    'active': 1.725,
    'extreme': 1.9,
    'walk-many': 1.35,
    'sport-twice': 1.8,
    'sitting-stress': 1.25,
    'poor-sleep': 1.15,
}

GOAL_MODIFIERS = {
    'lose-weight': 0.85,
    'maintain-weight': 1.0,
    'gain-weight': 1.15,
    'build-muscle': 1.2,
    'healthier': 0.98,
    'more-energy': 1.02,
    'less-sugar': 0.95,
    'cutting': 0.8,
    'fast-muscle-gain': 1.25,
    'better-sleep': 0.97,
    'less-fat': 0.94,
    'detox': 0.9,
}

MOOD_STYLES = {
    'stressed': ['comfort', 'light'],
    'happy': ['balanced', 'treat', 'comfort'],
    'sad': ['comfort', 'light'],
    'energetic': ['energizing', 'high-protein', 'carb-focused'],
    'hungry': ['hearty', 'comfort'],
    'sleepy': ['light', 'easy'],
    'angry': ['comfort'],
    'creative': ['inspired', 'treat'],
    'depressed': ['comfort', 'light'],
    'want-sweet': ['dessert', 'sweet'],
    'dont-want-cook': ['snack', 'ready'],
    'post-workout': ['high-protein', 'recovery'],
    'relax': ['comfort', 'treat'],
}

def estimate_bmr(profile: dict) -> float:
    age = profile.get('age', DEFAULT_PROFILE['age'])
    weight = profile.get('weight_kg', DEFAULT_PROFILE['weight_kg'])
    height = profile.get('height_cm', DEFAULT_PROFILE['height_cm'])
    sex = profile.get('sex', DEFAULT_PROFILE['sex'])
    if str(sex).lower().startswith('m'):
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    return max(1200, bmr)

def daily_calorie_target(profile: dict, goal: str) -> int:
    bmr = estimate_bmr(profile)
    activity = profile.get('activity', 'moderate')
    multi = ACTIVITY_MULTIPLIERS.get(activity, 1.55)
    base = bmr * multi
    goal_mod = GOAL_MODIFIERS.get(goal, 1.0)
    target = int(base * goal_mod)
    return target

# ----------------------------
# Menu planner with exclusion support
# ----------------------------
class MenuPlanner:
    def __init__(self, recipes: Optional[List[Recipe]] = None):
        load_sample_recipes()
        self.recipes = recipes if recipes is not None else RECIPES

    def score_recipe(self, recipe: Recipe, mood: str, goal: str) -> float:
        tag_score = recipe.matches(mood, goal)
        nut = recipe.nutrition
        if goal in ('lose-weight', 'cutting'):
            nutrition_score = max(0, 50 - (nut.calories / 10))
        elif goal in ('gain-weight', 'fast-muscle-gain', 'build-muscle'):
            nutrition_score = (nut.protein * 2) + (nut.calories / 50)
        else:
            nutrition_score = 20 - abs(nut.calories - 500) / 20
        rating_score = (recipe.rating or 0) * 1.2
        diversity = random.uniform(0, 5)
        score = tag_score * 1.5 + nutrition_score + diversity + rating_score
        return score

    def choose_meals(self, mood: str, goal: str, calories_target: int, forbidden: Optional[List[str]] = None) -> Dict[str, Recipe]:
        categories = ['breakfast', 'lunch', 'snack', 'dinner']
        chosen: Dict[str, Recipe] = {}
        used_ids = set()
        allocation = {'breakfast': 0.25, 'lunch': 0.35, 'snack': 0.1, 'dinner': 0.3}
        forbidden = [f.strip().lower() for f in (forbidden or []) if f.strip()]
        for cat in categories:
            target_cal = calories_target * allocation.get(cat, 0.25)
            candidates = [r for r in self.recipes if cat in [t.lower() for t in r.tags]]
            if not candidates:
                candidates = self.recipes[:]
            candidates = [r for r in candidates if not r.contains_forbidden(forbidden)]
            if not candidates:
                candidates = [r for r in self.recipes if not r.contains_forbidden(forbidden)]
            scored = []
            for r in candidates:
                if r.id in used_ids:
                    continue
                s = self.score_recipe(r, mood, goal) - abs(r.nutrition.calories - target_cal) / 50
                scored.append((s, r))
            scored.sort(key=lambda x: x[0], reverse=True)
            if scored:
                top_n = scored[:5]
                selected = random.choice(top_n)[1]
                chosen[cat] = selected
                used_ids.add(selected.id)
            else:
                available_recipes = [r for r in self.recipes if r.id not in used_ids]
                if available_recipes:
                    chosen[cat] = random.choice(available_recipes)
        return chosen

    def generate_plan(self, mood: str, goal: str, profile: dict, forbidden: Optional[List[str]] = None) -> dict:
        target = daily_calorie_target(profile, goal)
        meals = self.choose_meals(mood, goal, target, forbidden)
        total_nut = Nutrition(0, 0, 0, 0)
        for r in meals.values():
            total_nut += r.nutrition
        plan = {
            'date': datetime.date.today().isoformat(),
            'profile': profile,
            'goal': goal,
            'mood': mood,
            'calorie_target': target,
            'meals': {k: {'id': v.id, 'name_uk': v.name_uk, 'nutrition': v.nutrition.to_dict(), 'ingredients': v.ingredients, 'steps_uk': v.steps_uk, 'image': v.image, 'rating': v.rating, 'votes': v.votes} for k, v in meals.items()},
            'total_nutrition': total_nut.to_dict(),
        }
        return plan

# ----------------------------
# Shopping & explanation utilities
# ----------------------------
def build_shopping_list(plan: dict) -> Dict[str, float]:
    items: Dict[str, float] = {}
    for meal in plan['meals'].values():
        for ingr, qty in meal['ingredients'].items():
            try:
                items[ingr] = items.get(ingr, 0) + float(qty)
            except Exception:
                items[ingr] = items.get(ingr, 0) + 1
    return items

EXPLANATION_TEMPLATES_UK = [
    "Я підібрав це меню, бо ти зараз відчуваєш '{mood}', а мета — '{goal}'. Обрані страви: {highlights}.",
    "За профілем (вага {weight} кг, зріст {height} см, активність {activity}) добова потреба — ~{cal} ккал.",
]

def explain_plan_uk(plan: dict) -> str:
    mood = plan['mood']
    goal = plan['goal']
    profile = plan['profile']
    selected = [m['name_uk'] for m in plan['meals'].values()]
    highlights = ', '.join(selected)
    lines: List[str] = []
    lines.append(EXPLANATION_TEMPLATES_UK[0].format(mood=mood, goal=goal, highlights=highlights))
    lines.append(EXPLANATION_TEMPLATES_UK[1].format(weight=profile.get('weight_kg'), height=profile.get('height_cm'), activity=profile.get('activity'), cal=plan['calorie_target']))
    lines.append("Сумарно: {cal} ккал, білки {p:.1f} г, вуглеводи {c:.1f} г, жири {f:.1f} г.".format(cal=plan['total_nutrition']['calories'], p=plan['total_nutrition']['protein'], c=plan['total_nutrition']['carbs'], f=plan['total_nutrition']['fats']))
    return '\n'.join(lines)

# ----------------------------
# HTML template
# ----------------------------
HTML_TEMPLATE = """
<!doctype html>
<html lang="uk">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI-консультант із харчування</title>
    <style>
      :root{
        --bg:#f6f8fb; --card:#ffffff; --muted:#6b7280; --accent:#16a34a; --accent-2:#06b6d4;
        --glass: rgba(255,255,255,0.88);
        --nav-height:60px;
        --gap:10px;
        --radius:8px;
        --shadow: 0 6px 20px rgba(2,6,23,0.06);
        --small-font:13px;
      }
      *{box-sizing:border-box}
      body{
        margin:0; font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
        background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        color:#0f172a; padding:18px; padding-bottom:calc(var(--nav-height) + 18px);
      }
      .wrap{max-width:1050px;margin:0 auto}
      header{display:flex;align-items:center;gap:12px;margin-bottom:12px}
      .logo{width:44px;height:44px;border-radius:10px;background:linear-gradient(135deg,var(--accent),var(--accent-2));display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800}
      h1{margin:0;font-size:20px}
      .muted{color:var(--muted);font-size:var(--small-font)}
      .topcard{display:flex;gap:12px;background:var(--glass);padding:10px;border-radius:var(--radius);box-shadow:var(--shadow);align-items:flex-start}
      .panel{background:var(--card);border-radius:var(--radius);padding:10px;box-shadow:var(--shadow)}
      form input, form select, form textarea{width:100%;padding:8px;border-radius:6px;border:1px solid #e6eef6;font-size:14px}
      .controls{display:grid;grid-template-columns:1fr 320px;gap:12px}
      .bottom-nav{position:fixed;left:0;right:0;bottom:0;height:var(--nav-height);display:flex;align-items:center;justify-content:center;gap:8px;background:linear-gradient(90deg,rgba(255,255,255,0.95),rgba(255,255,255,0.9));box-shadow:0 -6px 24px rgba(2,6,23,0.06)}
      .nav-btn{padding:8px 14px;border-radius:10px;border:none;background:transparent;cursor:pointer;font-weight:700;font-size:14px}
      .nav-btn.active{background:linear-gradient(90deg,var(--accent),var(--accent-2));color:#fff}
      .hidden{display:none}
      /* compact recipe panel styles */
      .meal-panel{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;padding:10px;border-radius:8px}
      .meal-panel .meta{font-size:13px;color:var(--muted)}
      .meal-img {width:100px; height:100px; object-fit:cover; border-radius:6px; flex-shrink:0; background:#eee;}
      /* modal */
      .full-recipe-modal{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);width:92%;max-width:760px;max-height:82vh;overflow:auto;background:var(--card);border-radius:10px;padding:14px;box-shadow:0 30px 80px rgba(2,6,23,0.25);z-index:60}
      .modal-close{position:absolute;right:14px;top:10px;cursor:pointer;font-size:18px;z-index:10}
      .modal-img-banner {width:100%; height:200px; object-fit:cover; border-radius:8px; margin-bottom:12px; background:#eee;}
      /* dark theme */
      body.dark{background:linear-gradient(180deg,#07121a 0%, #04101a 100%);color:#e6eef6}
      body.dark .topcard{background:rgba(10,15,20,0.6)}
      body.dark .panel{background:#071827}
      body.dark .muted{color:#bcd0e3}
      body.dark .bottom-nav{background:linear-gradient(90deg,#02202a,#041827);box-shadow:0 -6px 24px rgba(0,0,0,0.5)}
      body.dark .nav-btn{color:#cfeaf3}
      body.dark .nav-btn.active{background:linear-gradient(90deg,#0b8f56,#0598b0);color:#fff}
      body.dark .full-recipe-modal{background:#071827;color:#e6eef6}
      body.dark .modal-close{color:#e6eef6}

      body.dark form input, body.dark form select{background:#0b1b22;color:#e6eef6;border:1px solid rgba(255,255,255,0.06)}
      body.dark [style*="color:#6b7280"]{color:#bcd0e3 !important}
      a { color: var(--accent-2); text-decoration: none }
      button.action { background: linear-gradient(90deg,var(--accent),var(--accent-2)); color: #fff; border: none; padding: 8px 10px; border-radius:8px; cursor:pointer; font-weight:700 }
      .compact-key { font-weight:700; font-size:13px; color:#0b1220 }
      body.dark .compact-key { color: #e6eef6 }
    
#page-myrecipes{
  background: linear-gradient(180deg,#f8fafc 0%,#eef2f7 100%);
  min-height: calc(100vh - 60px);
  padding-bottom:80px;
}
body.dark #page-myrecipes{
  background: linear-gradient(180deg,#07121a 0%,#04101a 100%);
}

</style>
  </head>
  <body>
    <div class="wrap">
      <header>
        <div class="logo">AI</div>
        <div style="flex:1">
          <h1>AI-консультант із харчування</h1>
          <div class="muted small">Меню під твій настрій та мету — з фото</div>
        </div>
        <div>
          <button onclick="toggleDark()" style="background:transparent;border:none;cursor:pointer;font-size:18px">🌗</button>
        </div>
      </header>

      <div id="page-home">
        <div class="topcard">
          <form method="post" action="/plan" id="planForm" style="width:100%">
            <div class="controls">
              <div class="panel">
                <div style="display:flex;gap:8px">
                  <div style="flex:1">
                    <label class="small">Вік</label>
                    <input name="age" type="number" min="10" max="120" value="{{ values.age or 30 }}">
                  </div>
                  <div style="width:120px">
                    <label class="small">Стать</label>
                    <select name="sex">
                      <option value="male" {% if values.sex=='male' %}selected{% endif %}>Чоловік</option>
                      <option value="female" {% if values.sex=='female' %}selected{% endif %}>Жінка</option>
                      <option value="other" {% if values.sex=='other' %}selected{% endif %}>Інше</option>
                    </select>
                  </div>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">
                  <div>
                    <label class="small">Вага (кг)</label>
                    <input name="weight_kg" type="number" step="0.1" value="{{ values.weight_kg or 75 }}">
                  </div>
                  <div>
                    <label class="small">Зріст (см)</label>
                    <input name="height_cm" type="number" step="1" value="{{ values.height_cm or 175 }}">
                  </div>
                </div>

                <div style="margin-top:8px">
                  <label class="small">Рівень активності</label>
                  <select name="activity">
                    <option value="sedentary" {% if values.activity=='sedentary' %}selected{% endif %}>Низька</option>
                    <option value="office" {% if values.activity=='office' %}selected{% endif %}>Офісна</option>
                    <option value="student" {% if values.activity=='student' %}selected{% endif %}>Учень</option>
                    <option value="light" {% if values.activity=='light' %}selected{% endif %}>Легка</option>
                    <option value="moderate" {% if values.activity=='moderate' %}selected{% endif %}>Помірна</option>
                    <option value="daily-sport" {% if values.activity=='daily-sport' %}selected{% endif %}>Щоденний спорт</option>
                    <option value="active" {% if values.activity=='active' %}selected{% endif %}>Висока</option>
                    <option value="extreme" {% if values.activity=='extreme' %}selected{% endif %}>Екстрим</option>
                    <option value="walk-many" {% if values.activity=='walk-many' %}selected{% endif %}>Багато ходжу</option>
                    <option value="sport-twice" {% if values.activity=='sport-twice' %}selected{% endif %}>Спорт 2×/день</option>
                    <option value="sitting-stress" {% if values.activity=='sitting-stress' %}selected{% endif %}>Сидяча + стрес</option>
                    <option value="poor-sleep" {% if values.activity=='poor-sleep' %}selected{% endif %}>Поганий сон</option>
                  </select>
                </div>

                <div style="display:flex;gap:8px;margin-top:8px">
                  <div style="flex:1">
                    <label class="small">Настрій</label>
                    <select name="mood">
                      <option value="happy" {% if values.mood=='happy' %}selected{% endif %}>Щасливий</option>
                      <option value="stressed" {% if values.mood=='stressed' %}selected{% endif %}>Стрес</option>
                      <option value="sad" {% if values.mood=='sad' %}selected{% endif %}>Сумний</option>
                      <option value="energetic" {% if values.mood=='energetic' %}selected{% endif %}>Енергійний</option>
                      <option value="hungry" {% if values.mood=='hungry' %}selected{% endif %}>Голодний</option>
                      <option value="sleepy" {% if values.mood=='sleepy' %}selected{% endif %}>Сонний</option>
                      <option value="want-sweet" {% if values.mood=='want-sweet' %}selected{% endif %}>Хочу солодкого</option>
                      <option value="dont-want-cook" {% if values.mood=='dont-want-cook' %}selected{% endif %}>Не хочу готувати</option>
                      <option value="post-workout" {% if values.mood=='post-workout' %}selected{% endif %}>Після тренування</option>
                      <option value="creative" {% if values.mood=='creative' %}selected{% endif %}>Творчий</option>
                    </select>
                  </div>
                  <div style="width:220px">
                    <label class="small">Мета</label>
                    <select name="goal">
                      <option value="lose-weight" {% if values.goal=='lose-weight' %}selected{% endif %}>Схуднення</option>
                      <option value="maintain-weight" {% if values.goal=='maintain-weight' %}selected{% endif %}>Тримати вагу</option>
                      <option value="gain-weight" {% if values.goal=='gain-weight' %}selected{% endif %}>Набір ваги</option>
                      <option value="build-muscle" {% if values.goal=='build-muscle' %}selected{% endif %}>Побудова м'язів</option>
                      <option value="healthier" {% if values.goal=='healthier' %}selected{% endif %}>Здоровіше</option>
                      <option value="more-energy" {% if values.goal=='more-energy' %}selected{% endif %}>Більше енергії</option>
                      <option value="less-sugar" {% if values.goal=='less-sugar' %}selected{% endif %}>Менше цукру</option>
                      <option value="cutting" {% if values.goal=='cutting' %}selected{% endif %}>Сушка</option>
                      <option value="fast-muscle-gain" {% if values.goal=='fast-muscle-gain' %}selected{% endif %}>Швидкий набір м'язів</option>
                      <option value="better-sleep" {% if values.goal=='better-sleep' %}selected{% endif %}>Краще засинання</option>
                      <option value="detox" {% if values.goal=='detox' %}selected{% endif %}>Детокс</option>
                    </select>
                  </div>
                </div>

                <div style="margin-top:8px">
                  
                </div>
              </div>

              <div class="panel" style="display:flex;flex-direction:column;justify-content:space-between;gap:8px">
                <div>
                  <div class="small" style="margin-bottom:8px"><strong>Резерв: рецепти приховано</strong></div>
                  <div class="small">Великий каталог рецептів приховано з головної сторінки.</div>
                </div>
                <div style="display:flex;flex-direction:column;gap:8px">
                  <button type="submit" class="action">Згенерувати план</button>
                  <button type="button" onclick="savePlan()" style="background:transparent;border:1px solid #e6eef6;padding:8px;border-radius:8px;cursor:pointer">Зберегти план</button>
                  <a href="/export_shopping" id="exportLink" class="small">Експорт списку покупок</a>
                </div>
              </div>
            </div>
          
            <div style="margin-top:10px">
              <label class="small">Параметри — виключити інгредієнти (наприклад: яйця, риба, молоко)</label>
              <input id="forbiddenInput" name="notes" placeholder="Напиши через кому що виключити..." value="{{ values.notes or '' }}">
            </div>
    </form>
        </div>

        {% if plan %}
        <script>
          window.LAST_PLAN = {{ plan | tojson | safe }};
        </script>
        <div style="margin-top:12px;display:flex;gap:12px">
          <div style="flex:1">
            <div style="display:flex;justify-content:space-between;align-items:flex-end;">
              <div>
                <div class="small">Дата</div>
                <div style="font-weight:800">{{ plan.date }}</div>
                <div class="small">Ціль: {{ plan.calorie_target }} ккал</div>
              </div>
              <div class="small">Профіль: {{ plan.profile.weight_kg }}кг • {{ plan.profile.height_cm }}см</div>
            </div>

            <h3 style="margin:10px 0 6px 0">Обране меню</h3>
            <div style="display:grid;grid-template-columns:1fr;gap:8px">
              {% for key, meal in plan.meals.items() %}
              <div class="panel meal-panel" data-mealid="{{ meal.id }}" data-image="{{ meal.image }}">
                {% if meal.image %}
                  <img src="{{ meal.image }}" alt="{{ meal.name_uk }}" class="meal-img" loading="lazy">
                {% else %}
                  <div class="meal-img" style="display:flex;align-items:center;justify-content:center;color:#ccc">No IMG</div>
                {% endif %}
                <div style="flex:1">
                  <div class="compact-key">{{ key.title() }} — {{ meal.name_uk }}</div>
                  <div style="margin-top:6px" class="small">Інгредієнти: 
                    {% for ik, iv in meal.ingredients.items() %}{{ ik }} — {{ iv }}{% if not loop.last %}, {% endif %}{% endfor %}
                  </div>
                  <div style="margin-top:6px" class="small">Кроки: 
                    <ol style="margin:6px 0 0 18px; padding:0">
                      {% for s in meal.steps_uk %}
                        <li style="margin-bottom:4px;font-size:13px">{{ s }}</li>
                      {% endfor %}
                    </ol>
                  </div>
                </div>
                <div style="min-width:110px;text-align:right">
                  <div style="font-weight:700">{{ meal.nutrition.calories }} ккал</div>
                  <div class="small">Б {{ meal.nutrition.protein }} • В {{ meal.nutrition.carbs }} • Ж {{ meal.nutrition.fats }}</div>
                  <div style="margin-top:8px;display:flex;flex-direction:column;gap:6px">
                    <button onclick="showFullRecipe('{{ meal.id }}')" style="background:transparent;border:none;cursor:pointer">Як приготувати</button>
                    <button onclick="saveRecipeToMyRecipes('{{ meal.id }}','{{ meal.name_uk|escape }}')" style="background:transparent;border:none;cursor:pointer">Зберегти рецепт</button>
                  </div>
                </div>
              </div>
              {% endfor %}
            </div>
          </div>

          <aside style="width:320px;display:flex;flex-direction:column;gap:8px">
            <div class="panel">
              <h4 style="margin:0 0 8px 0">Пояснення</h4>
              <pre style="white-space:pre-wrap;font-family:inherit;margin:0" class="small">{{ explanation }}</pre>
            </div>

            <div class="panel">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <h4 style="margin:0">Список покупок</h4>
                <div>
                  <button onclick="copyShopping()" style="background:transparent;border:none;cursor:pointer" class="small">Копіювати</button>
                  <a href="/download_shopping" target="_blank" class="small" style="margin-left:6px">CSV</a>
                </div>
              </div>
              <ul id="shoppingList" style="margin-top:8px;font-size:13px">
                {% for k, v in shopping.items() %}
                  <li>{{ k }} — {{ v }}</li>
                {% endfor %}
              </ul>
            </div>
          </aside>
        </div>
        {% else %}
        <script>
          window.LAST_PLAN = null;
        </script>
        {% endif %}

        </div>

      
      <div id="page-parameters" class="hidden">
        <div class="panel">
          <h3>Параметри</h3>
          <div class="small muted">Виключити інгредієнти (наприклад: яйця, риба, молоко)</div>
          <div style="margin-top:8px">
            
          </div>
          <div style="margin-top:10px; display:flex; gap:8px;">
            <button onclick="saveParams()" class="action">Зберегти параметри</button>
            <button onclick="clearParams()" style="background:transparent;border:1px solid #e6eef6;padding:8px;border-radius:8px;cursor:pointer">Очистити</button>
          </div>
        </div>
      </div>
<div id="page-myrecipes" class="hidden">
        <div class="panel">
          <h3>Мої збережені рецепти та плани</h3>
          <div id="myRecipesList" class="small muted">Тут будуть збережені рецепти та плани (localStorage).</div>
        </div>
      </div>

      <div id="page-profile" class="hidden">
        <div class="panel">
          <h3>Профіль</h3>
          <div class="small muted">Налаштування профілю (локально).</div>
          <div style="margin-top:8px;display:flex;gap:8px">
            <button onclick="clearSavedData()" style="background:transparent;border:1px solid #e6eef6;padding:8px;border-radius:8px;cursor:pointer">Очистити збережені дані</button>
            <button onclick="exportAllSaved()" class="action">Експорт усіх планів</button>
          </div>
        </div>
      </div>

      <div id="fullRecipeModal" class="full-recipe-modal hidden" aria-hidden="true">
        <div style="position:relative">
          <div class="modal-close" onclick="closeFullRecipe()">✕</div>
          <img id="fullRecipeImage" class="modal-img-banner hidden">
          <h3 id="fullRecipeTitle">Рецепт</h3>
          <div id="fullRecipeBody" class="small"></div>
        </div>
      </div>

    </div>

    <div class="bottom-nav" role="navigation">
      <button class="nav-btn active" id="nav-home" onclick="showPage('home')">Головна</button>
      <button class="nav-btn" id="nav-myrecipes" onclick="showPage('myrecipes')">Мої рецепти</button>
      
    </div>

    <script>
      const form = document.getElementById('planForm');
      const STORAGE_KEY = 'ai_nutrition_form_v5';
      function saveFormToStorage(){
        try{
          const fd = new FormData(form);
          const obj = {};
          for(const [k,v] of fd.entries()) obj[k]=v;
          localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
        }catch(e){ console.warn('saveForm',e) }
      }
      function loadFormFromStorage(){
        try{
          const raw = localStorage.getItem(STORAGE_KEY);
          if(!raw) return;
          const obj = JSON.parse(raw);
          for(const k in obj){
            const el = form.elements[k];
            if(!el) continue;
            el.value = obj[k];
          }
        }catch(e){ console.warn('loadFormFromStorage',e) }
      }
      form && form.addEventListener('change', saveFormToStorage);
      setInterval(saveFormToStorage, 2000);
      loadFormFromStorage();

      function copyShopping(){
        const items = Array.from(document.querySelectorAll('#shoppingList li')).map(li => li.textContent.trim()).join('\\n');
        navigator.clipboard && navigator.clipboard.writeText(items).then(()=>{alert('Список покупок скопійовано');}).catch(()=>{alert('Не вдалося скопіювати');});
      }

      function toggleDark(){
        document.body.classList.toggle('dark');
        localStorage.setItem('ai_theme_dark', document.body.classList.contains('dark'));
      }
      if(localStorage.getItem('ai_theme_dark') === 'true') document.body.classList.add('dark');

      // Parameters (forbidden ingredients) persistence
      function saveParams(){
        try{
          const val = document.getElementById('forbiddenInput') ? document.getElementById('forbiddenInput').value : '';
          localStorage.setItem('ai_params_forbidden', val || '');
          alert('Параметри збережено');
        }catch(e){ console.warn(e); alert('Не вдалося зберегти параметри'); }
      }
      function clearParams(){
        if(confirm('Очистити параметри?')){
          localStorage.removeItem('ai_params_forbidden');
          const el = document.getElementById('forbiddenInput');
          if(el) el.value='';
        }
      }
      // load saved params to the input when page loads
      try{
        const saved = localStorage.getItem('ai_params_forbidden') || '';
        const inp = document.getElementById('forbiddenInput');
        if(inp && saved) inp.value = saved;
      }catch(e){console.warn(e)}
      // ensure notes (forbidden) are included when saving the main form: keep STORAGE_KEY behaviour
      // when planForm saved, incorporate forbidden input value
      const originalSave = saveFormToStorage;
      saveFormToStorage = function(){
        try{
          originalSave && originalSave();
          const raw = localStorage.getItem(STORAGE_KEY) || '{}';
          const obj = JSON.parse(raw);
          obj['notes'] = (document.getElementById('forbiddenInput') ? document.getElementById('forbiddenInput').value : obj['notes'] || '');
          localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
        }catch(e){ console.warn(e) }
      }
      // load the notes into forbiddenInput when loading form
      const originalLoad = loadFormFromStorage;
      loadFormFromStorage = function(){
        try{
          originalLoad && originalLoad();
          const raw = localStorage.getItem(STORAGE_KEY) || '{}';
          const obj = JSON.parse(raw);
          const inp = document.getElementById('forbiddenInput');
          if(inp && obj['notes']) inp.value = obj['notes'];
        }catch(e){ console.warn(e) }
      }
      // call load after definition
      loadFormFromStorage();


      function savePlan(){
        try{
          if(!window.LAST_PLAN){
            alert('Немає плану для збереження. Згенеруй план спочатку.');
            return;
          }
          const raw = localStorage.getItem('ai_saved_plans') || '[]';
          const arr = JSON.parse(raw);
          const obj = { id: 'plan_' + Date.now(), name: 'План ' + new Date().toLocaleDateString(), saved_at: new Date().toISOString(), payload: window.LAST_PLAN };
          arr.unshift(obj);
          localStorage.setItem('ai_saved_plans', JSON.stringify(arr));
          alert('План збережено в "Мої рецепти"');
        }catch(e){ console.warn(e); alert('Не вдалося зберегти план');}
      }

      function saveRecipeToMyRecipes(id, name){
        try{
          const rawRecipes = localStorage.getItem('ai_my_recipes') || '[]';
          const arr = JSON.parse(rawRecipes);
          if(arr.find(r=>r.id===id)){ alert('Вже збережено'); return; }
          const card = document.querySelector('[data-mealid=\"'+id+'\"]');
          let details = { id:id, name:name, saved_at: new Date().toISOString(), ingredients:[], steps:[], image:"", nutrition:null };
          if(card){
            details.image = card.getAttribute('data-image') || "";
            const ingEls = card.querySelectorAll('ul li');
            if(ingEls && ingEls.length){
              ingEls.forEach(li => details.ingredients.push(li.textContent.trim()));
            } else {
              const text = card.innerText || '';
              const m = text.match(/Інгредієнти:\\s*([^\\n]+)/i);
              if(m && m[1]) {
                m[1].split(',').forEach(it => details.ingredients.push(it.trim()));
              }
            }
            const stepEls = card.querySelectorAll('ol li');
            if(stepEls && stepEls.length){
              stepEls.forEach(li => details.steps.push(li.textContent.trim()));
            }
          }
          arr.push(details);
          localStorage.setItem('ai_my_recipes', JSON.stringify(arr));
          alert('Рецепт збережено в "Мої рецепти"');
        }catch(e){ console.warn(e); alert('Не вдалося зберегти рецепт'); }
      }

      function renderMyRecipes(){
        const container = document.getElementById('myRecipesList');
        const rawR = localStorage.getItem('ai_my_recipes') || '[]';
        const rawP = localStorage.getItem('ai_saved_plans') || '[]';
        const arrR = JSON.parse(rawR);
        const arrP = JSON.parse(rawP);
        container.innerHTML = '';
        if(!arrR.length && !arrP.length){
          container.innerHTML = '<p class=\"small muted\">Ще немає збережених рецептів чи планів.</p>';
          return;
        }

        if(arrP.length){
          const h = document.createElement('h4'); h.textContent = 'Збережені плани'; container.appendChild(h);
          arrP.forEach(p=>{
            const el = document.createElement('div'); el.style.padding='8px'; el.style.borderBottom='1px solid rgba(0,0,0,0.06)';
            const title = document.createElement('div'); title.textContent = p.name; title.style.fontWeight='700';
            const meta = document.createElement('div'); meta.textContent = new Date(p.saved_at).toLocaleString(); meta.className='small muted';
            const btns = document.createElement('div'); btns.style.marginTop='6px';
            const openBtn = document.createElement('button'); openBtn.textContent='Відкрити'; openBtn.style.marginRight='8px';
            openBtn.onclick = ()=>{ openSavedPlanModal(p.id); showPage('myrecipes'); };
            const delBtn = document.createElement('button'); delBtn.textContent='Видалити';
            delBtn.onclick = ()=>{ if(confirm('Видалити цей план?')){ removeSavedPlan(p.id); renderMyRecipes(); } };
            btns.appendChild(openBtn); btns.appendChild(delBtn);
            el.appendChild(title); el.appendChild(meta); el.appendChild(btns);
            container.appendChild(el);
          });
        }

        if(arrR.length){
          const h2 = document.createElement('h4'); h2.textContent = 'Збережені рецепти'; container.appendChild(h2);
          arrR.forEach(r=>{
            const el = document.createElement('div'); el.style.padding='8px'; el.style.borderBottom='1px solid rgba(0,0,0,0.06)';
            
            const row = document.createElement('div'); row.style.display='flex'; row.style.gap='8px';
            if(r.image){
                const img = document.createElement('img'); img.src = r.image; img.style.width='50px'; img.style.height='50px'; img.style.objectFit='cover'; img.style.borderRadius='4px';
                row.appendChild(img);
            }
            const txt = document.createElement('div');
            const title = document.createElement('div'); title.textContent = r.name; title.style.fontWeight='700';
            const meta = document.createElement('div'); meta.textContent = new Date(r.saved_at).toLocaleString(); meta.className='small muted';
            txt.appendChild(title); txt.appendChild(meta);
            row.appendChild(txt);
            el.appendChild(row);

            const btns = document.createElement('div'); btns.style.marginTop='6px';
            const openBtn = document.createElement('button'); openBtn.textContent='Відкрити рецепт'; openBtn.style.marginRight='8px';
            openBtn.onclick = ()=>{ showSavedRecipe(r.id); showPage('myrecipes'); };
            const delBtn = document.createElement('button'); delBtn.textContent='Видалити';
            delBtn.onclick = ()=>{ if(confirm('Видалити рецепт?')){ removeMyRecipe(r.id); renderMyRecipes(); } };
            btns.appendChild(openBtn); btns.appendChild(delBtn);
            el.appendChild(btns);
            container.appendChild(el);
          });
        }
      }

      function removeMyRecipe(id){
        const raw = localStorage.getItem('ai_my_recipes') || '[]';
        const arr = JSON.parse(raw).filter(r=>r.id!==id);
        localStorage.setItem('ai_my_recipes', JSON.stringify(arr));
      }

      function removeSavedPlan(id){
        const raw = localStorage.getItem('ai_saved_plans') || '[]';
        const arr = JSON.parse(raw).filter(p=>p.id!==id);
        localStorage.setItem('ai_saved_plans', JSON.stringify(arr));
      }

      function clearSavedData(){
        if(confirm('Очистити всі збережені рецепти та плани?')){
          localStorage.removeItem('ai_my_recipes');
          localStorage.removeItem('ai_saved_plans');
          alert('Очистжено');
        }
      }

      function exportAllSaved(){
        try{
          const r = localStorage.getItem('ai_my_recipes') || '[]';
          const p = localStorage.getItem('ai_saved_plans') || '[]';
          const all = { recipes: JSON.parse(r), plans: JSON.parse(p) };
          const blob = new Blob([JSON.stringify(all, null, 2)], {type:'application/json'});
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url; a.download = 'ai_saved_all.json'; a.click(); URL.revokeObjectURL(url);
        }catch(e){ alert('Не вдалося експортувати'); }
      }

      function showPage(page){
        document.querySelectorAll('#page-home, #page-myrecipes').forEach(el=>el.classList.add('hidden'));
        document.getElementById('page-'+page).classList.remove('hidden');
        document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
        document.getElementById('nav-'+page).classList.add('active');
        if(page==='myrecipes') renderMyRecipes();
      }

      function findRecipeCardById(id){
        return document.querySelector('[data-mealid=\"'+id+'\"]');
      }

      function showFullRecipe(id){
        const modal = document.getElementById('fullRecipeModal');
        const titleEl = document.getElementById('fullRecipeTitle');
        const bodyEl = document.getElementById('fullRecipeBody');
        const imgEl = document.getElementById('fullRecipeImage');

        imgEl.classList.add('hidden'); 
        imgEl.src = '';

        const card = findRecipeCardById(id);
        if(card){
          const nameEl = card.querySelector('.compact-key') || card.querySelector('h4');
          const name = nameEl ? nameEl.textContent.trim() : id;
          titleEl.textContent = name;
          
          const imgSrc = card.getAttribute('data-image');
          if(imgSrc){
            imgEl.src = imgSrc;
            imgEl.classList.remove('hidden');
          }

          let html = '';
          const ingMatch = card.innerText.match(/Інгредієнти:\\s*([^\\n]+)/i);
          if(ingMatch && ingMatch[1]){
            const parts = ingMatch[1].split(',');
            html += '<h4 style=\"margin-top:0\">Інгредієнти</h4><ul>';
            parts.forEach(p=> html += '<li>'+p.trim()+'</li>');
            html += '</ul>';
          } else {
            const ul = card.querySelectorAll('ul li');
            if(ul && ul.length){
              html += '<h4 style=\"margin-top:0\">Інгредієнти</h4><ul>';
              ul.forEach(li => html += '<li>'+li.textContent+'</li>');
              html += '</ul>';
            }
          }
          const steps = card.querySelectorAll('ol li');
          if(steps && steps.length){
            html += '<h4>Кроки приготування</h4><ol>';
            steps.forEach(li => html += '<li>'+li.textContent+'</li>');
            html += '</ol>';
          }
          if(!html) html = '<div class=\"small muted\">Деталі рецептів відсутні.</div>';
          bodyEl.innerHTML = html;
          modal.classList.remove('hidden'); modal.setAttribute('aria-hidden','false');
          return;
        }

        try{
          const raw = localStorage.getItem('ai_my_recipes') || '[]';
          const arr = JSON.parse(raw);
          const found = arr.find(r=>r.id===id);
          if(found){
            titleEl.textContent = found.name;
            if(found.image){
                imgEl.src = found.image;
                imgEl.classList.remove('hidden');
            }
            let html = '';
            if(found.ingredients && found.ingredients.length){
              html += '<h4 style=\"margin-top:0\">Інгредієнти</h4><ul>';
              found.ingredients.forEach(it=> html += '<li>'+it+'</li>');
              html += '</ul>';
            }
            if(found.steps && found.steps.length){
              html += '<h4>Кроки приготування</h4><ol>';
              found.steps.forEach(s=> html += '<li>'+s+'</li>');
              html += '</ol>';
            }
            if(!html) html = '<div class=\"small muted\">Деталі рецепту збережено не повністю.</div>';
            bodyEl.innerHTML = html;
            modal.classList.remove('hidden'); modal.setAttribute('aria-hidden','false');
            return;
          }
        }catch(e){ console.warn(e); }

        alert('Рецепт не знайдено.');
      }

      function closeFullRecipe(){
        const modal = document.getElementById('fullRecipeModal');
        modal.classList.add('hidden'); modal.setAttribute('aria-hidden','true');
      }

      function openSavedPlanModal(id){
        try{
          const raw = localStorage.getItem('ai_saved_plans') || '[]';
          const arr = JSON.parse(raw);
          const found = arr.find(p=>p.id===id);
          if(!found){ alert('План не знайдено'); return; }
          const plan = found.payload;
          const titleEl = document.getElementById('fullRecipeTitle');
          const bodyEl = document.getElementById('fullRecipeBody');
          const imgEl = document.getElementById('fullRecipeImage');
          
          imgEl.classList.add('hidden'); 
          titleEl.textContent = found.name;
          let html = '<div class=\"small\">Збережено: ' + new Date(found.saved_at).toLocaleString() + '</div>';
          html += '<h4>План ('+plan.calorie_target+' ккал)</h4>';
          for(const [k, meal] of Object.entries(plan.meals)){
            html += '<div style=\"margin-top:12px; border-bottom:1px solid #eee; padding-bottom:8px\">';
            if(meal.image) {
                html += '<img src="'+meal.image+'" style="width:60px;height:60px;object-fit:cover;border-radius:4px;float:left;margin-right:8px">';
            }
            html += '<strong>'+k+': '+meal.name_uk+'</strong>';
            if(meal.ingredients){
              html += '<div style=\"margin-top:6px;clear:both\"><em>Інгредієнти:</em><ul>';
              for(const [ik, iv] of Object.entries(meal.ingredients)) html += '<li>'+ik+' — '+iv+'</li>';
              html += '</ul></div>';
            }
            html += '</div>';
          }
          bodyEl.innerHTML = html;
          document.getElementById('fullRecipeModal').classList.remove('hidden');
        }catch(e){ console.warn(e); alert('Не вдалося відкрити план'); }
      }

      function showSavedRecipe(id){
        try{
          const raw = localStorage.getItem('ai_my_recipes') || '[]';
          const arr = JSON.parse(raw);
          const found = arr.find(r=>r.id===id);
          if(!found){ alert('Рецепт не знайдено'); return; }
          document.getElementById('fullRecipeTitle').textContent = found.name;
          const imgEl = document.getElementById('fullRecipeImage');
          if(found.image){
              imgEl.src = found.image;
              imgEl.classList.remove('hidden');
          } else { imgEl.classList.add('hidden'); }
          
          let html = '';
          if(found.ingredients && found.ingredients.length){
            html += '<h4 style=\"margin-top:0\">Інгредієнти</h4><ul>';
            found.ingredients.forEach(it=> html += '<li>'+it+'</li>');
            html += '</ul>';
          }
          if(found.steps && found.steps.length){
            html += '<h4>Кроки приготування</h4><ol>';
            found.steps.forEach(s=> html += '<li>'+s+'</li>');
            html += '</ol>';
          }
          if(!html) html = '<div class=\"small muted\">Деталі рецепту відсутні.</div>';
          document.getElementById('fullRecipeBody').innerHTML = html;
          document.getElementById('fullRecipeModal').classList.remove('hidden');
        }catch(e){ alert('Не вдалося відкрити рецепт'); }
      }
    </script>
  </body>
</html>
"""

# ----------------------------
# Flask endpoints
# ----------------------------
def run_flask(host='127.0.0.1', port=5000):
    if not FLASK_AVAILABLE:
        print("Flask is not installed. Install with: pip install flask")
        return
    load_sample_recipes()
    app = Flask(__name__)
    planner = MenuPlanner(RECIPES)

    SERVER_STATE = {'last_plan': None, 'last_shopping_csv': None}

    @app.route('/', methods=['GET'])
    def index():
        values = DEFAULT_PROFILE.copy()
        values.update({'mood': 'happy', 'goal': 'maintain-weight', 'notes': ''})
        return render_template_string(HTML_TEMPLATE, values=values, RECIPES=RECIPES)

    @app.route('/plan', methods=['POST'])
    def plan():
        try:
            profile = {
                'age': int(request.form.get('age', 30)),
                'sex': request.form.get('sex', 'male'),
                'weight_kg': float(request.form.get('weight_kg', 75)),
                'height_cm': float(request.form.get('height_cm', 175)),
                'activity': request.form.get('activity', 'moderate'),
            }
        except Exception:
            profile = DEFAULT_PROFILE.copy()
        mood = request.form.get('mood', 'happy')
        goal = request.form.get('goal', 'maintain-weight')
        notes = request.form.get('notes', '')
        forbidden = []
        if notes:
            parts = []
            for part in notes.split(','):
                for sub in part.split(';'):
                    parts.extend(sub.split('/'))
            forbidden = [p.strip().lower() for p in parts if p.strip()]
        the_plan = planner.generate_plan(mood, goal, profile, forbidden)
        shopping = build_shopping_list(the_plan)
        explanation = explain_plan_uk(the_plan)
        values = profile.copy()
        values.update({'mood': mood, 'goal': goal, 'notes': notes})
        try:
            si = io.StringIO()
            cw = csv.writer(si)
            cw.writerow(['Інгредієнт', 'Кількість'])
            for k, v in shopping.items():
                cw.writerow([k, v])
            SERVER_STATE['last_shopping_csv'] = si.getvalue()
            SERVER_STATE['last_plan'] = the_plan
        except Exception:
            SERVER_STATE['last_shopping_csv'] = None
        return render_template_string(HTML_TEMPLATE, plan=the_plan, shopping=shopping, explanation=explanation, values=values, RECIPES=RECIPES)

    @app.route('/export_shopping', methods=['GET'])
    def export_shopping():
        txt = SERVER_STATE.get('last_shopping_csv') or ''
        if not txt:
            return "Немає списку покупок. Згенеруйте план спочатку.", 400
        resp = make_response(txt)
        resp.headers["Content-Disposition"] = "attachment; filename=shopping.csv"
        resp.headers["Content-Type"] = "text/csv; charset=utf-8"
        return resp

    @app.route('/download_shopping', methods=['GET'])
    def download_shopping():
        txt = SERVER_STATE.get('last_shopping_csv') or ''
        if not txt:
            return "Немає списку покупок.", 400
        mem = io.BytesIO()
        mem.write(txt.encode('utf-8'))
        mem.seek(0)
        return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='shopping.csv')

    @app.route('/api/plan', methods=['POST'])
    def api_plan():
        payload = request.get_json(force=True)
        profile = {
            'age': int(payload.get('age', 30)),
            'sex': payload.get('sex', 'male'),
            'weight_kg': float(payload.get('weight_kg', 75)),
            'height_cm': float(payload.get('height_cm', 175)),
            'activity': payload.get('activity', 'moderate'),
        }
        mood = payload.get('mood', 'happy')
        goal = payload.get('goal', 'maintain-weight')
        forbidden = payload.get('forbidden', []) or []
        the_plan = planner.generate_plan(mood, goal, profile, forbidden)
        return jsonify(the_plan)

    @app.route('/save_plan', methods=['POST'])
    def save_plan():
        payload = request.get_json(force=True)
        try:
            path = os.path.join(os.getcwd(), f"saved_plan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return jsonify({'ok': True, 'path': path})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500

    @app.route('/rate', methods=['POST'])
    def rate():
        recipe_id = request.form.get('recipe_id')
        try:
            value = float(request.form.get('value', '0'))
        except Exception:
            value = 0.0
        found = None
        for r in RECIPES:
            if r.id == recipe_id:
                found = r
                break
        if not found:
            return jsonify({'ok': False, 'error': 'recipe not found'}), 404
        found.add_rating(value)
        return jsonify({'ok': True, 'rating': found.rating, 'votes': found.votes})

    print(f"Starting server at http://{host}:{port}")
    app.run(host=host, port=port)

# ----------------------------
# CLI demo
# ----------------------------
def run_demo_cli():
    load_sample_recipes()
    planner = MenuPlanner(RECIPES)
    p = DEFAULT_PROFILE.copy()
    plan = planner.generate_plan('energetic', 'maintain-weight', p)
    print(json.dumps(plan, ensure_ascii=False, indent=2))

# ----------------------------
# Entry point
# ----------------------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description='AI Nutrition Consultant (updated: AI photos)')
    parser.add_argument('--serve', action='store_true', help='Run web server (Flask)')
    parser.add_argument('--demo', action='store_true', help='Run demo CLI')
    args = parser.parse_args()
    if args.serve:
        run_flask()
    elif args.demo:
        run_demo_cli()
    else:
        print("No mode specified. Use --serve to run the web UI or --demo to run CLI demo.")

if __name__ == '__main__':
    main()