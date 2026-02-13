from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import random
from datetime import datetime

app = FastAPI(
    title="🎲 Fun API",
    description="An exciting API with random generators, magic 8-ball, and more!",
    version="1.0.0"
)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎲 Fun API</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #eee;
            padding: 2rem;
        }
        h1 {
            text-align: center;
            font-size: 3rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { text-align: center; color: #888; margin-bottom: 2rem; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.3);
        }
        .card h2 { font-size: 1.5rem; margin-bottom: 1rem; }
        .card-content { min-height: 60px; margin-bottom: 1rem; }
        .result {
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
            padding: 1rem;
            font-size: 1.1rem;
            line-height: 1.5;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            transition: opacity 0.2s, transform 0.1s;
            width: 100%;
        }
        button:hover { opacity: 0.9; }
        button:active { transform: scale(0.98); }
        input {
            width: 100%;
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(0,0,0,0.3);
            color: white;
            font-size: 1rem;
            margin-bottom: 0.75rem;
        }
        input::placeholder { color: #888; }
        .input-row {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }
        .input-row input { margin-bottom: 0; }
        .lucky-nums { color: #feca57; font-weight: bold; }
        .disclaimer { font-size: 0.85rem; color: #48dbfb; margin-top: 0.5rem; }
        .emoji-big { font-size: 2rem; }
        a { color: #48dbfb; }
    </style>
</head>
<body>
    <h1>🎲 Fun API</h1>
    <p class="subtitle">Click buttons to have some fun! | <a href="/docs">API Docs</a></p>
    
    <div class="grid">
        <div class="card">
            <h2>🔮 Fortune</h2>
            <div class="card-content"><div class="result" id="fortune-result">Click to reveal your fortune...</div></div>
            <button onclick="getFortune()">Get Fortune</button>
        </div>
        
        <div class="card">
            <h2>🎱 Magic 8-Ball</h2>
            <div class="card-content">
                <input type="text" id="question" placeholder="Ask a yes/no question...">
                <div class="result" id="8ball-result">The mystic 8-ball awaits...</div>
            </div>
            <button onclick="ask8Ball()">Ask</button>
        </div>
        
        <div class="card">
            <h2>😄 Dad Jokes</h2>
            <div class="card-content"><div class="result" id="joke-result">Ready for a groan-worthy joke?</div></div>
            <button onclick="getJoke()">Tell Me a Joke</button>
        </div>
        
        <div class="card">
            <h2>🎲 Dice Roller</h2>
            <div class="card-content">
                <div class="input-row">
                    <input type="number" id="dice-count" value="2" min="1" max="20" placeholder="Count">
                    <input type="number" id="dice-sides" value="6" min="2" max="100" placeholder="Sides">
                </div>
                <div class="result" id="dice-result">Roll the dice!</div>
            </div>
            <button onclick="rollDice()">Roll!</button>
        </div>
        
        <div class="card">
            <h2>🪙 Coin Flip</h2>
            <div class="card-content"><div class="result" id="flip-result"><span class="emoji-big">🪙</span></div></div>
            <button onclick="flipCoin()">Flip!</button>
        </div>
        
        <div class="card">
            <h2>🔢 Random Number</h2>
            <div class="card-content">
                <div class="input-row">
                    <input type="number" id="rand-min" value="1" placeholder="Min">
                    <input type="number" id="rand-max" value="100" placeholder="Max">
                </div>
                <div class="result" id="random-result">Pick a number, any number...</div>
            </div>
            <button onclick="getRandomNumber()">Generate</button>
        </div>
        
        <div class="card">
            <h2>🔥 Roast Me</h2>
            <div class="card-content"><div class="result" id="roast-result">Feeling brave?</div></div>
            <button onclick="getRoast()">Roast Me!</button>
        </div>
        
        <div class="card">
            <h2>💐 Compliment</h2>
            <div class="card-content"><div class="result" id="compliment-result">Need a pick-me-up?</div></div>
            <button onclick="getCompliment()">Compliment Me!</button>
        </div>
        
        <div class="card">
            <h2>✊✋✂️ Rock Paper Scissors</h2>
            <div class="card-content">
                <div class="input-row" style="justify-content:center;gap:1rem;">
                    <button onclick="playRPS('rock')" style="width:auto;padding:0.5rem 1rem;">✊</button>
                    <button onclick="playRPS('paper')" style="width:auto;padding:0.5rem 1rem;">✋</button>
                    <button onclick="playRPS('scissors')" style="width:auto;padding:0.5rem 1rem;">✂️</button>
                </div>
                <div class="result" id="rps-result">Choose your weapon!</div>
            </div>
        </div>
        
        <div class="card">
            <h2>🔐 Password Generator</h2>
            <div class="card-content">
                <div class="input-row">
                    <input type="number" id="pw-length" value="16" min="8" max="64" placeholder="Length">
                    <label style="display:flex;align-items:center;gap:0.5rem;color:#888;">
                        <input type="checkbox" id="pw-symbols" checked> Symbols
                    </label>
                </div>
                <div class="result" id="password-result" style="font-family:monospace;word-break:break-all;">Click to generate...</div>
            </div>
            <button onclick="getPassword()">Generate</button>
        </div>
        
        <div class="card">
            <h2>🤔 Would You Rather</h2>
            <div class="card-content"><div class="result" id="wyr-result">Dev edition dilemmas await...</div></div>
            <button onclick="getWYR()">Give Me a Dilemma</button>
        </div>
    </div>
    
    <div id="confetti-container"></div>
    
    <script>
        async function getFortune() {
            const res = await fetch('/fortune').then(r => r.json());
            document.getElementById('fortune-result').innerHTML = 
                `${res.fortune}<br><span class="lucky-nums">Lucky numbers: ${res.lucky_numbers.join(', ')}</span>`;
        }
        
        async function ask8Ball() {
            const q = document.getElementById('question').value || 'Will I be lucky today?';
            const res = await fetch(`/8ball?question=${encodeURIComponent(q)}`).then(r => r.json());
            document.getElementById('8ball-result').innerHTML = `<strong>"${res.question}"</strong><br><br>🎱 ${res.answer}`;
        }
        
        async function getJoke() {
            const res = await fetch('/joke').then(r => r.json());
            document.getElementById('joke-result').textContent = res.joke;
        }
        
        async function rollDice() {
            const count = document.getElementById('dice-count').value || 2;
            const sides = document.getElementById('dice-sides').value || 6;
            const res = await fetch(`/roll?count=${count}&sides=${sides}`).then(r => r.json());
            document.getElementById('dice-result').innerHTML = 
                `<strong>${res.dice}</strong>: [${res.rolls.join(', ')}]<br>Total: <strong>${res.total}</strong>`;
        }
        
        async function flipCoin() {
            const el = document.getElementById('flip-result');
            el.innerHTML = '<span class="emoji-big">🪙</span>';
            el.style.transition = 'transform 0.5s';
            el.style.transform = 'rotateY(720deg)';
            await new Promise(r => setTimeout(r, 500));
            const res = await fetch('/flip').then(r => r.json());
            el.innerHTML = `<span class="emoji-big">${res.emoji}</span><br>${res.result}!`;
            el.style.transform = 'rotateY(0deg)';
        }
        
        async function getRandomNumber() {
            const min = document.getElementById('rand-min').value || 1;
            const max = document.getElementById('rand-max').value || 100;
            const res = await fetch(`/random-number?min=${min}&max=${max}`).then(r => r.json());
            document.getElementById('random-result').innerHTML = `<span style="font-size:2rem;font-weight:bold">${res.number}</span><br>(${res.range})`;
        }
        
        async function getRoast() {
            const res = await fetch('/roast').then(r => r.json());
            document.getElementById('roast-result').innerHTML = `${res.roast}<p class="disclaimer">${res.disclaimer}</p>`;
        }
        
        async function getCompliment() {
            const res = await fetch('/compliment').then(r => r.json());
            document.getElementById('compliment-result').textContent = res.compliment;
            confetti();
        }
        
        async function playRPS(choice) {
            const res = await fetch(`/rps?choice=${choice}`).then(r => r.json());
            const el = document.getElementById('rps-result');
            el.innerHTML = `${res.you} vs ${res.cpu}<br><strong>${res.message}</strong>`;
            if (res.result === 'win') confetti();
        }
        
        async function getPassword() {
            const len = document.getElementById('pw-length').value || 16;
            const sym = document.getElementById('pw-symbols').checked;
            const res = await fetch(`/password?length=${len}&symbols=${sym}`).then(r => r.json());
            const el = document.getElementById('password-result');
            el.innerHTML = `${res.password}<br><span style="color:#48dbfb;">Strength: ${res.strength}</span>`;
            navigator.clipboard.writeText(res.password).catch(()=>{});
        }
        
        async function getWYR() {
            const res = await fetch('/would-you-rather').then(r => r.json());
            document.getElementById('wyr-result').innerHTML = 
                `<strong>Would you rather...</strong><br><br>
                 🅰️ ${res.option_a}<br><em>or</em><br>🅱️ ${res.option_b}?`;
        }
        
        function confetti() {
            const container = document.getElementById('confetti-container');
            const colors = ['#ff6b6b','#feca57','#48dbfb','#ff9ff3','#1dd1a1','#5f27cd'];
            for (let i = 0; i < 50; i++) {
                const c = document.createElement('div');
                c.style.cssText = `
                    position:fixed; width:10px; height:10px; 
                    background:${colors[Math.floor(Math.random()*colors.length)]};
                    left:${Math.random()*100}vw; top:-10px; border-radius:50%;
                    animation: fall ${1+Math.random()*2}s ease-out forwards;
                    opacity:${0.5+Math.random()*0.5};
                `;
                container.appendChild(c);
                setTimeout(() => c.remove(), 3000);
            }
        }
        
        // Enter key support for 8-ball
        document.getElementById('question').addEventListener('keypress', e => { if(e.key === 'Enter') ask8Ball(); });
    </script>
    <style>
        @keyframes fall {
            to { transform: translateY(105vh) rotate(720deg); opacity: 0; }
        }
        #confetti-container { position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none; z-index:9999; }
    </style>
</body>
</html>
"""


@app.get("/ui", response_class=HTMLResponse)
def frontend():
    """Interactive web UI"""
    return HTML_PAGE

# Fun data
FORTUNES = [
    "A beautiful, smart, and loving person will be coming into your life.",
    "A dubious friend may be an enemy in camouflage.",
    "A faithful friend is a strong defense.",
    "A fresh start will put you on your way.",
    "A golden egg of opportunity falls into your lap this month.",
    "Your code will compile on the first try today.",
    "A senior developer will mass-approve your PRs.",
    "You will find the bug in the last place you look.",
]

MAGIC_8_BALL = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful."
]

DAD_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "Why do Java developers wear glasses? Because they can't C#!",
    "A SQL query walks into a bar, walks up to two tables and asks, 'Can I join you?'",
    "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
    "There are only 10 types of people in the world: those who understand binary and those who don't.",
    "Why do Python programmers have low self-esteem? They're constantly comparing themselves to others.",
    "What's a programmer's favorite hangout place? Foo Bar!",
]

WOULD_YOU_RATHER = [
    ("mass-delete production database", "mass-reply-all to entire company"),
    ("only code in Comic Sans", "only use a 13-inch monitor forever"),
    ("debug code with no stack traces", "write code with no autocomplete"),
    ("have all your PRs rejected", "have all your PRs auto-approved without review"),
    ("only use vim", "only use nano"),
    ("work on legacy PHP forever", "rewrite everything in assembly"),
    ("have 100 easy bugs", "have 1 impossible heisenbug"),
    ("attend meetings all day", "answer Slack messages all day"),
]


@app.get("/")
def home():
    return {
        "message": "🎉 Welcome to the Fun API!",
        "endpoints": {
            "/fortune": "Get your fortune",
            "/8ball?question=...": "Ask the Magic 8-Ball",
            "/joke": "Get a dad joke",
            "/roll?sides=6&count=1": "Roll some dice",
            "/flip": "Flip a coin",
            "/random-number?min=1&max=100": "Get a random number",
            "/roast": "Get roasted (lovingly)",
            "/compliment": "Get a compliment",
        }
    }


@app.get("/fortune")
def get_fortune():
    """🔮 Get your fortune for the day"""
    return {
        "fortune": random.choice(FORTUNES),
        "lucky_numbers": random.sample(range(1, 50), 5)
    }


@app.get("/8ball")
def magic_8_ball(question: str = Query(..., description="Your yes/no question")):
    """🎱 Ask the Magic 8-Ball a question"""
    return {
        "question": question,
        "answer": random.choice(MAGIC_8_BALL)
    }


@app.get("/joke")
def get_joke():
    """😄 Get a programming dad joke"""
    return {"joke": random.choice(DAD_JOKES)}


@app.get("/roll")
def roll_dice(
    sides: int = Query(6, ge=2, le=100, description="Number of sides on each die"),
    count: int = Query(1, ge=1, le=20, description="Number of dice to roll")
):
    """🎲 Roll some dice"""
    rolls = [random.randint(1, sides) for _ in range(count)]
    return {
        "dice": f"{count}d{sides}",
        "rolls": rolls,
        "total": sum(rolls)
    }


@app.get("/flip")
def flip_coin():
    """🪙 Flip a coin"""
    result = random.choice(["Heads", "Tails"])
    return {"result": result, "emoji": "👑" if result == "Heads" else "🦅"}


@app.get("/random-number")
def random_number(
    min: int = Query(1, description="Minimum value"),
    max: int = Query(100, description="Maximum value")
):
    """🔢 Get a random number in a range"""
    if min > max:
        min, max = max, min
    return {"number": random.randint(min, max), "range": f"{min}-{max}"}


@app.get("/roast")
def get_roast():
    """🔥 Get lovingly roasted"""
    roasts = [
        "Your code works, but so does a car held together with duct tape.",
        "I've seen better error handling in a 'Hello World' program.",
        "Your git commits read like a mystery novel no one wants to solve.",
        "You mass-import libraries like you're preparing for the apocalypse.",
        "Your variable naming convention is 'whatever I feel like today'.",
    ]
    return {"roast": random.choice(roasts), "disclaimer": "Just kidding, you're great! 💙"}


@app.get("/compliment")
def get_compliment():
    """💐 Get a nice compliment"""
    compliments = [
        "Your code is so clean it makes Marie Kondo jealous.",
        "You debug with the precision of a surgeon.",
        "Your documentation is actually useful. That's rare!",
        "You're the kind of developer who makes code reviews enjoyable.",
        "Your commit messages tell a beautiful story.",
    ]
    return {"compliment": random.choice(compliments)}


@app.get("/rps")
def rock_paper_scissors(choice: str = Query(..., description="rock, paper, or scissors")):
    """✊✋✂️ Play Rock Paper Scissors"""
    choice = choice.lower().strip()
    if choice not in ["rock", "paper", "scissors"]:
        return {"error": "Choose rock, paper, or scissors!"}
    
    cpu = random.choice(["rock", "paper", "scissors"])
    emoji_map = {"rock": "✊", "paper": "✋", "scissors": "✂️"}
    
    if choice == cpu:
        result = "tie"
    elif (choice == "rock" and cpu == "scissors") or \
         (choice == "paper" and cpu == "rock") or \
         (choice == "scissors" and cpu == "paper"):
        result = "win"
    else:
        result = "lose"
    
    return {
        "you": f"{emoji_map[choice]} {choice}",
        "cpu": f"{emoji_map[cpu]} {cpu}",
        "result": result,
        "message": {"win": "🎉 You win!", "lose": "😢 You lose!", "tie": "🤝 It's a tie!"}[result]
    }


@app.get("/password")
def generate_password(
    length: int = Query(16, ge=8, le=64, description="Password length"),
    symbols: bool = Query(True, description="Include symbols")
):
    """🔐 Generate a secure password"""
    import string
    chars = string.ascii_letters + string.digits
    if symbols:
        chars += "!@#$%^&*"
    password = ''.join(random.choice(chars) for _ in range(length))
    strength = "weak" if length < 12 else "medium" if length < 16 else "strong"
    return {"password": password, "length": length, "strength": strength}


@app.get("/would-you-rather")
def would_you_rather():
    """🤔 Get a Would You Rather dilemma"""
    option_a, option_b = random.choice(WOULD_YOU_RATHER)
    return {"option_a": option_a, "option_b": option_b}
