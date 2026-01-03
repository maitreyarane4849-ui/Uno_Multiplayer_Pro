# uno_launcher.py
# Single-file launcher: writes index.html, style.css, uno.js to a temp folder,
# starts a local HTTP server and opens the game in the default browser.

import os
import tempfile
import threading
import http.server
import socketserver
import webbrowser
import socket

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>UNO Multiplayer Pro</title>
  <link rel="stylesheet" href="style.css"/>
</head>
<body>
  <div id="game-container">
    <h1>UNO Multiplayer Pro</h1>

    <div id="setup">
      <label>Number of players (1-4): 
        <input id="numPlayers" type="number" min="1" max="4" value="2">
      </label>
      <label><input type="checkbox" id="botOption"> Play with bot</label>

      <!--  New: Difficulty selector -->
      <div id="difficulty-container" style="display:none;">
        <label>Bot Difficulty: 
          <select id="botDifficulty">
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>
      </div>

      <button id="startBtn">Start Game</button>
    </div>

    <div id="game" style="display:none;">
      <div id="discard-section">
        <h2>Discard Pile</h2>
        <div id="discard"></div>
        <button id="drawBtn">Draw Card</button>
      </div>
      <div id="player-section"></div>
      <div id="status"></div>
    </div>
  </div>

  <script src="uno.js"></script>

  <!-- Script to show/hide difficulty -->
  <script>
    document.getElementById("botOption").addEventListener("change", function() {
      document.getElementById("difficulty-container").style.display =
        this.checked ? "block" : "none";
    });
  </script>
</body>
</html>
"""

STYLE_CSS = """body {
  background: linear-gradient(135deg, #4f8cff 0%, #ffb84d 100%);
  font-family: 'Segoe UI', Arial, sans-serif;
  margin: 0;
  padding: 0;
}

#game-container {
  max-width: 900px;
  margin: 24px auto;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(40,60,80,0.2);
  padding: 24px;
}

h1 {
  text-align: center;
  color: #3b4d8c;
}

#setup {
  text-align: center;
  margin-bottom: 32px;
}

#game {
  margin-top: 24px;
}

#discard-section {
  text-align: center;
  margin-bottom: 24px;
}

#discard {
  display: inline-block;
  min-width: 80px;
  min-height: 120px;
  border: 2px solid #333;
  border-radius: 8px;
  background: #eee;
  font-size: 1.3rem;
  color: #222;
  margin-bottom: 8px;
  padding: 14px;
}

#player-section {
  display: flex;
  flex-wrap: wrap;
  gap: 32px;
  justify-content: center;
}

.player-area {
  background: #f0f6ff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(120,120,120,0.10);
  padding: 18px 12px 12px 12px;
  min-width: 220px;
  margin-bottom: 16px;
  text-align: center;
}

.player-title {
  font-weight: bold;
  color: #3b4d8c;
  margin-bottom: 10px;
}

.hand {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: center;
}

.card {
  background: #fff;
  border: 2px solid #888;
  border-radius: 8px;
  padding: 10px 8px 5px 8px;
  min-width: 54px;
  min-height: 74px;
  font-size: 1.1rem;
  font-weight: bold;
  cursor: pointer;
  margin-bottom: 6px;
  transition: transform 0.1s;
  box-shadow: 0 2px 12px rgba(80,80,80,0.10);
  user-select: none;
}

.card.red { background: #ff6666; color: #fff; border-color: #c00;}
.card.green { background: #5edc98; color: #fff; border-color: #197a43;}
.card.yellow { background: #ffe066; color: #333; border-color: #c7a520;}
.card.blue { background: #5ca7ff; color: #fff; border-color: #1254a3;}
.card.wild { background: linear-gradient(45deg,#444,#f8f8f8); color: #222; border-color: #333;}

.card:hover {
  transform: scale(1.08);
  opacity: 0.94;
  z-index: 2;
}

#status {
  margin-top: 16px;
  padding: 8px;
  text-align: center;
  font-size: 1.14rem;
  color: #2b2b2b;
  background: #eaf0ff;
  border-radius: 8px;
  min-height: 34px;
}

button {
  padding: 8px 20px;
  font-size: 1rem;
  background: #3b4d8c;
  color: #fff;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  margin: 4px;
  transition: background 0.12s;
}

button:hover {
  background: #2c3a6a;
}

/* Style for difficulty selector */
#difficulty-container {
  margin-top: 12px;
}
#difficulty-container label {
  font-weight: 500;
  color: #3b4d8c;
}
#botDifficulty {
  margin-left: 6px;
  padding: 6px;
  border-radius: 6px;
  border: 1px solid #ccc;
}
/* Fix for large zoom on open */
html {
  zoom: 0.85; /* Adjust: try 0.8–0.9 for perfect size */
  transform-origin: top center;
}

#game-container {
  transform: scale(0.95);
  transform-origin: top center;
}
/* hidden/back of a card (neutral look so color is not visible) */
.card.back {
  background: linear-gradient(135deg, #444, #666);
  color: #fff !important;
  border-color: #333 !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.45);
  text-align: center;
  font-weight: bold;
}

/* optional small icon for back-only view */
.card.back::after{
  content: "🂠";
  display: block;
  font-size: 1.4rem;
  line-height: 1;
  margin-top: 6px;
}
"""

UNO_JS = """// UNO Multiplayer Pro - With Bot Difficulty Levels (Easy / Medium / Hard)

const COLORS = ["Red", "Green", "Yellow", "Blue"];
const VALUES = [0,1,2,3,4,5,6,7,8,9,"Draw Two","Skip","Reverse"];
const WILDS = ["Wild","Wild Draw Four"];

let deck = [];
let discards = [];
let players = [];
let currentColor = null;
let currentValue = null;
let playerTurn = 0;
let playDirection = 1;
let playing = false;
let botActive = false;
let botDifficulty = "easy"; //  New variable

function buildDeck() {
  let d = [];
  for (let color of COLORS) {
    for (let value of VALUES) {
      d.push({color, value});
      if (value !== 0) d.push({color, value});
    }
  }
  for (let i = 0; i < 4; i++) {
    d.push({color: "Wild", value: "Wild"});
    d.push({color: "Wild", value: "Wild Draw Four"});
  }
  return d;
}

function shuffleDeck(deck) {
  for (let i = deck.length - 1; i > 0; i--) {
    let j = Math.floor(Math.random() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck;
}

function drawCards(num) {
  let cards = [];
  for (let i = 0; i < num; i++) {
    if (deck.length === 0) {
      let top = discards.pop();
      deck = shuffleDeck([...discards]);
      discards = [top];
    }
    cards.push(deck.shift());
  }
  return cards;
}

function canPlay(card, color, value) {
  if (card.color === "Wild") return true;
  if (card.color === color) return true;
  if (card.value === value) return true;
  return false;
}

function setupGame(nPlayers, botOption) {
  deck = shuffleDeck(buildDeck());
  deck = shuffleDeck(deck);
  discards = [];
  players = [];
  botActive = false;

  if (nPlayers === 1 && botOption) {
    players.push(drawCards(7)); // Player
    players.push(drawCards(7)); // Bot
    botActive = true;
    botDifficulty = document.getElementById("botDifficulty").value; // Get difficulty
    console.log("Bot difficulty set to:", botDifficulty);
  } else {
    for (let i = 0; i < nPlayers; i++) {
      players.push(drawCards(7));
    }
  }

  discards.push(deck.shift());
  let splitCard = discards[0];
  currentColor = splitCard.color !== "Wild" ? splitCard.color : COLORS[Math.floor(Math.random()*COLORS.length)];
  currentValue = splitCard.value;
  playerTurn = 0;
  playDirection = 1;
  playing = true;
  renderGame();
  updateStatus(`Game started! Player 1's turn.`);
  if (botActive && playerTurn === 1) setTimeout(botPlay, 900);
}

function cardHTML(card) {
  let colorClass = card.color.toLowerCase().replace(" ","");
  return `<div class="card ${colorClass}">${card.color === "Wild" ? card.value : `${card.color}<br>${card.value}`}</div>`;
}

function renderGame() {
  document.getElementById("discard").innerHTML = cardHTML(discards[discards.length-1]);
  let playerSection = document.getElementById("player-section");
  playerSection.innerHTML = "";
  for (let i = 0; i < players.length; i++) {
    let area = document.createElement("div");
    area.className = "player-area";
    let title = document.createElement("div");
    title.className = "player-title";
    let isBot = botActive && i === 1;
    title.textContent = isBot ? `Bot (${players[i].length} cards)${i===playerTurn?" ←":""}` : `Player ${i+1} (${players[i].length} cards)${i===playerTurn?" ←":""}`;
    area.appendChild(title);

    let handDiv = document.createElement("div");
    handDiv.className = "hand";

    for (let j = 0; j < players[i].length; j++) {
      let card = players[i][j];
      let cdiv = document.createElement("div");

      // Only show face for the active human player's hand.
      // For bots and other opponents, show neutral back.
      let showFace = (i === playerTurn) && !(botActive && i === 1);

      if (showFace) {
        cdiv.className = "card " + (card.color.toLowerCase().replace(" ","") || "wild");
        cdiv.innerHTML = card.color === "Wild" ? card.value : `${card.color}<br>${card.value}`;
        if (playing && canPlay(card, currentColor, currentValue)) {
          cdiv.style.cursor = "pointer";
          cdiv.onclick = () => playCard(j);
        } else {
          cdiv.style.cursor = "not-allowed";
          cdiv.style.opacity = "0.6";
        }
      } else {
        // neutral back: no color class
        cdiv.className = "card back";
        cdiv.innerHTML = ""; // .card.back::after shows icon
        cdiv.style.cursor = "not-allowed";
        cdiv.style.opacity = "1";
      }

      handDiv.appendChild(cdiv);
    }

    area.appendChild(handDiv);
    playerSection.appendChild(area);
  }
}

function playCard(idx) {
  let card = players[playerTurn][idx];
  if (!canPlay(card, currentColor, currentValue)) return;
  players[playerTurn].splice(idx,1);
  discards.push(card);

  // If wild, ask player for color and set it
  if (card.color === "Wild") {
    let clr = prompt("Choose color: Red, Green, Blue, Yellow", COLORS[0]);
    clr = (COLORS.includes(clr)) ? clr : COLORS[0];
    currentColor = clr;
  } else {
    currentColor = card.color;
  }
  currentValue = card.value;

  let msg = `Player ${playerTurn+1} played ${card.color} ${card.value}. `;

  // Effect flags
  let skipNext = false;

  if (card.value === "Reverse") {
    playDirection *= -1;
    msg += "Direction reversed. ";
    if (players.length === 2) skipNext = true; // Reverse acts like skip in 2-player
  }
  if (card.value === "Skip") {
    msg += "Next player skipped. ";
    skipNext = true;
  }
  if (card.value === "Draw Two") {
    let next = (playerTurn + playDirection + players.length) % players.length;
    players[next].push(...drawCards(2));
    msg += `Player ${next+1} draws 2. `;
    skipNext = true;
  }
  if (card.value === "Wild Draw Four") {
    let next = (playerTurn + playDirection + players.length) % players.length;
    players[next].push(...drawCards(4));
    msg += `Player ${next+1} draws 4. `;
    skipNext = true;
  }

  // Check for win
  if (players[playerTurn].length === 0) {
    playing = false;
    updateStatus(`Player ${playerTurn+1}${botActive && playerTurn === 1 ? " (Bot)" : ""} wins! 🎉`);
    renderGame();
    return;
  }

  // Advance turn only once, accounting for skip
  let advanceBy = skipNext ? 2 : 1;
  playerTurn = (playerTurn + playDirection * advanceBy + players.length) % players.length;

  renderGame();
  updateStatus(msg + `${botActive && playerTurn === 1 ? "Bot's" : "Player " + (playerTurn+1) + "'s"} turn.`);
  if (botActive && playerTurn === 1 && playing) setTimeout(botPlay, 900);
}

function updateStatus(msg) {
  document.getElementById("status").textContent = msg;
}

//  Enhanced Bot Logic (Easy / Medium / Hard)
function botPlay() {
  if (!playing) return;
  let botHand = players[1];
  let playableCards = botHand.filter(c => canPlay(c, currentColor, currentValue));

  if (playableCards.length === 0) {
    players[1].push(...drawCards(1));
    updateStatus(`Bot drew a card.`);
    // After drawing, bot's turn ends
  } else {
    let chosenIdx = null;

    if (botDifficulty === "easy") {
      chosenIdx = botHand.indexOf(playableCards[Math.floor(Math.random() * playableCards.length)]);
    } else if (botDifficulty === "medium") {
      let normalCards = playableCards.filter(c => c.color !== "Wild");
      let pick = normalCards.length > 0 ? normalCards[Math.floor(Math.random() * normalCards.length)] : playableCards[0];
      chosenIdx = botHand.indexOf(pick);
    } else if (botDifficulty === "hard") {
      // Choose color with highest count in bot's hand (excluding wilds)
      let colorCount = {};
      botHand.forEach(c => {
        if (c.color !== "Wild") colorCount[c.color] = (colorCount[c.color] || 0) + 1;
      });
      // Determine best color: fallback to currentColor or first available color
      let bestColor = currentColor || Object.keys(colorCount)[0] || COLORS[0];
      // prefer a playable card that matches bestColor
      let preferred = playableCards.find(c => c.color === bestColor) || playableCards[0];
      chosenIdx = botHand.indexOf(preferred);
    }

    // Safety: if chosenIdx for any reason is -1, choose random playable index
    if (chosenIdx === -1 || chosenIdx === null) {
      chosenIdx = botHand.indexOf(playableCards[Math.floor(Math.random() * playableCards.length)]);
    }

    let chosenCard = botHand[chosenIdx];
    updateStatus(`Bot (${botDifficulty}) played ${chosenCard.color} ${chosenCard.value}.`);
    playCard(chosenIdx);
    return;
  }

  // advance to next player after bot's action if bot didn't already call playCard
  playerTurn = (playerTurn + playDirection + players.length) % players.length;
  renderGame();
  updateStatus(`Player ${playerTurn+1}'s turn.`);
}

document.getElementById("startBtn").onclick = () => {
  let nPlayers = parseInt(document.getElementById("numPlayers").value,10);
  let botOption = document.getElementById("botOption").checked;
  if (nPlayers < 1 || nPlayers > 4) {
    alert("Players must be 1-4.");
    return;
  }
  if (nPlayers === 1 && !botOption) {
    alert("Single player mode requires bot enabled.");
    return;
  }
  document.getElementById("setup").style.display = "none";
  document.getElementById("game").style.display = "block";
  setupGame(nPlayers, botOption);
};

document.getElementById("drawBtn").onclick = () => {
  if (!playing) return;
  if (botActive && playerTurn === 1) return;
  players[playerTurn].push(...drawCards(1));
  let msg = `Player ${playerTurn+1} drew a card. `;
  playerTurn = (playerTurn + playDirection + players.length) % players.length;
  renderGame();
  updateStatus(msg + `${botActive && playerTurn === 1 ? "Bot's" : "Player " + (playerTurn+1) + "'s"} turn.`);
  if (botActive && playerTurn === 1 && playing) setTimeout(botPlay, 900);
};
"""

def find_free_port():
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def write_files(folder):
    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)
    with open(os.path.join(folder, "style.css"), "w", encoding="utf-8") as f:
        f.write(STYLE_CSS)
    with open(os.path.join(folder, "uno.js"), "w", encoding="utf-8") as f:
        f.write(UNO_JS)

class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # suppress logging to keep console clean
        pass

def start_server(folder, port):
    os.chdir(folder)
    handler = QuietHTTPRequestHandler
    # Threading server so browser can request files concurrently
    with socketserver.ThreadingTCPServer(("", port), handler) as httpd:
        print(f"Serving UNO Multiplayer Pro at http://localhost:{port}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass

def main():
    tmp = tempfile.mkdtemp(prefix="uno_game_")
    write_files(tmp)
    port = find_free_port()
    thread = threading.Thread(target=start_server, args=(tmp, port), daemon=True)
    thread.start()

    url = f"http://localhost:{port}/index.html"
    print("Opening game in default browser...")
    webbrowser.open_new_tab(url)
    print("If your browser blocks popups, open this URL manually:")
    print(url)
    print("\nPress ENTER in this console to stop the server and exit.")
    try:
        input()
    except KeyboardInterrupt:
        pass
    print("Shutting down...")

if __name__ == "__main__":
    main()

