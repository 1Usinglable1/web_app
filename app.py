from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
import json
import csv
from io import StringIO
from functools import wraps
import json
from pathlib import Path

MONSTERS_FILE = Path('data/monsters.json')

# Загрузка монстров из файла
def load_monsters():
    try:
        with open(MONSTERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Сохранение монстров в файл
def save_monsters(monsters):
    MONSTERS_FILE.parent.mkdir(exist_ok=True)
    with open(MONSTERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(monsters, f, ensure_ascii=False, indent=2)

# Загружаем монстров при старте
MONSTERS = load_monsters()

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Mock data
WITCHER_DATA = {
    "name": "Геральт из Ривии",
    "school": "Волка",
    "signs": ["Игни", "Аард", "Квен", "Аксий", "Ирден"],
    "stats": {
        "toxicity": 75,
        "health": 100,
        "stamina": 85,
        "attack_power": 90
    },
    "inventory": {
        "swords": {
            "steel": "Меч из зеркального сплава",
            "silver": "Аэндрит"
        },
        "armor": "Доспехи школы Волка",
        "alchemy": ["Черная кровь", "Золотая иволга", "Тигр"]
    },
    "active_quests": ["Убить чудовище в Боклере", "Найти Цири"]
}

ALCHEMY_ITEMS = [
    {"name": "Черная кровь", "type": "potion", "toxicity": 40},
    {"name": "Золотая иволга", "type": "potion", "toxicity": 30},
    {"name": "Тигр", "type": "potion", "toxicity": 50},
    {"name": "Драконья мечта", "type": "bomb", "toxicity": 20},
    {"name": "Лунная пыль", "type": "bomb", "toxicity": 15}
]

MONSTERS = [
    {"name": "Стрыга", "type": "проклятый", "weakness": "Серебро"},
    {"name": "Дракоид", "type": "рептилия", "weakness": "Игни"},
    {"name": "Утопец", "type": "некроид", "weakness": "Серебро"}
]

CONTRACTS = [
    {"monster": "Стрыга", "reward": 500, "date": "2023-10-15"},
    {"monster": "Дракоид", "reward": 300, "date": "2023-10-20"},
    {"monster": "Утопец", "reward": 200, "date": "2023-10-25"}
]


# Helper functions
def load_reviews():
    try:
        with open('data/reviews.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_reviews(reviews):
    with open('data/reviews.json', 'w') as f:
        json.dump(reviews, f)


def school_required(school):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'school' not in session or session['school'] != school:
                return "Доступ запрещен: только для школы {}".format(school), 403
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def master_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'rank' not in session or session['rank'] != 'Master':
            return "Доступ запрещен: требуется ранг Мастера", 403
        return f(*args, **kwargs)

    return decorated_function


# Routes
@app.route('/')
def index():
    return render_template('profile.html', witcher=WITCHER_DATA)


@app.route('/alchemy')
def alchemy():
    item_type = request.args.get('type')
    toxicity = request.args.get('toxicity', type=int)

    filtered_items = ALCHEMY_ITEMS
    if item_type:
        filtered_items = [item for item in filtered_items if item['type'] == item_type]
    if toxicity:
        filtered_items = [item for item in filtered_items if item['toxicity'] >= toxicity]

    return jsonify([item['name'] for item in filtered_items])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['school'] = request.form['school']
        session['rank'] = request.form.get('rank', 'Новичок')
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/kaermorhen')
@school_required('Волка')
def kaermorhen():
    return "Добро пожаловать в Каэр Морхен, ведьмак школы Волка!"


@app.route('/contracts')
@master_required
def contracts():
    return render_template('contracts.html', contracts=CONTRACTS, calculate_total_gold=calculate_total_gold)


@app.route('/contracts/report')
@master_required
def contracts_report():
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Монстр', 'Награда', 'Дата'])
    cw.writerows([(c['monster'], c['reward'], c['date']) for c in CONTRACTS])

    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=contracts_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@app.route('/quests', methods=['GET', 'POST'])
def quests():
    reviews = load_reviews()

    if request.method == 'POST':
        review = {
            'quest': request.form['quest'],
            'rating': int(request.form['rating']),
            'comment': request.form['comment'],
            'author': session.get('school', 'Аноним')
        }
        reviews.append(review)
        save_reviews(reviews)

    return render_template('quests.html', reviews=reviews)


@app.route('/witcher/stats')
def witcher_stats():
    return jsonify({
        'equipment':
            { 'swords': WITCHER_DATA['inventory']['swords'],
            'armor': WITCHER_DATA['inventory']['armor'],
            'alchemy': WITCHER_DATA['inventory']['alchemy']
        },
        'toxicity': WITCHER_DATA['stats']['toxicity'],
        'active_quests': WITCHER_DATA['active_quests']
        })


# CLI commands
@app.cli.command('add_monster')
def add_monster():
    """Добавить монстра в бестиарий"""
    name = input("Имя монстра: ")
    monster_type = input("Тип монстра: ")
    weakness = input("Слабость: ")

    MONSTERS.append({
        "name": name,
        "type": monster_type,
        "weakness": weakness
    })
    save_monsters(MONSTERS)  # Сохраняем в файл
    print(f"Монстр {name} добавлен в бестиарий!")


@app.cli.command('remove_monster')
def remove_monster():
    """Удалить монстра по имени"""
    name = input("Имя монстра для удаления: ")
    global MONSTERS
    MONSTERS = [m for m in MONSTERS if m['name'] != name]
    save_monsters(MONSTERS)  # Сохраняем в файл
    print(f"Монстр {name} удален из бестиария!")


@app.cli.command('find_monsters')
def find_monsters():
    """Найти монстров по слабости"""
    weakness = input("Слабость (Серебро/Игни): ")
    found = [m for m in MONSTERS if m['weakness'] == weakness]
    print(f"Найдено {len(found)} монстров:")
    for m in found:
        print(f"- {m['name']} ({m['type']})")


def calculate_total_gold(contracts):
    return sum(c['reward'] for c in contracts)


if __name__ == '__main__':
    app.run(debug=True)