# conf-chat

A simple peer-to-peer chat with one **global chat room** and **private direct messages (DMs)**. There is no central server: every user runs a node, and all messages live in a shared **Kademlia distributed hash table (DHT)** spread across the nodes.

## P2P framework

- **Kademlia** via the Python [`kademlia`](https://github.com/bmuller/kademlia) library (`pip install kademlia`)

### Why Kademlia instead of OpenChord

I'm stronger in Python than Java, and OpenChord is a Java library. However, both could be used to accomplish the function of this project.

## Installation

Requires Python 3.9+. and Kademlia. This was done using a .txt once in my case

```bash
git clone <your-fork-url>
cd conf-chat
pip install -r requirements.txt
```

## Running

Start at least one extra node first. A Kademlia node with no peers has nowhere to store data, and this extra node keeps stored messages available while users come and go. It is a normal peer, not a server: any node can be used to join the network.

```bash
#In my experience you must set up a virtual environment first on a Linux setup
python3 -m venv venv
source venv/bin/activate
# Terminal 1: a node with no chat prompt
python conf_chat.py --port 8468 --relay

# Terminal 2, 3, ...: a chat node per user, joining through any running node
python conf_chat.py --port 8469 --bootstrap 127.0.0.1:8468
python conf_chat.py --port 8470 --bootstrap 127.0.0.1:8468
```

Each chat node asks for your name, then you can start chatting. Nodes can be added or removed at any time without reconfiguring anything. To run across machines, use the other machine's IP in `--bootstrap`.

## Using it

| Input | What it does |
|---|---|
| any text | Sends the message to everyone in the global chat |
| `/dm <name> <message>` | Sends a private message to one user |
| `/users` | Lists everyone who has joined |
| `/help` | Shows the list of commands |
| `/quit` | Exits |

## Use case

I simplified the suggested use case to focus on the core P2P messaging:

- **Global chat (many-to-many):** every user can send to and receive from one shared room. You see messages sent after you join.
- **Direct messages (two-way):** any user can privately message any other user by name. If the recipient is online, the message appears within about 2 seconds. If they are offline, they get it the next time they start the app with the same name, even if the sender has left.
- Users identify themselves by typing a name at startup. There are no stored accounts. The focus of this program was that chat rather than having a system tht stored that information.

## Design

All data is stored in the DHT as JSON under these keys:

| Key | Value |
|---|---|
| `chat` | The global chat room: a list of every message (`from`, `text`) |
| `inbox:<name>` | A list of every DM sent to that user |
| `seen:<name>` | How many DMs that user has already read |
| `users` | Every name that has joined (added once, on first start) |

How it works:

- **Sending** appends a message to the `chat` list or to the recipient's `inbox`.
- **Receiving:** every node checks the room and its own inbox every 2 seconds and prints anything new.
- **Offline DMs:** the DM read position is stored in the DHT, not on the user's machine, so DMs that arrived while you were away show up when you return. Messages live in the DHT, not on the sender's machine, so the sender can leave without losing them.

## AI Disclosure

AI was used to learn about Kamedlia to better integrate it into this project.

## Known limitations

- **No authentication:** anyone can type any name, so they could read another user's DMs. Any node can also write any key in the DHT. Messages are not encrypted.
- **Concurrent updates:** lists are updated by read-modify-write. If two people send to the same list at the same moment, one message can be lost. This is most likely in a busy global chat. A production system would need versioning or per-message keys.
- **Peers leaving:** when a node quits, the others keep trying to contact it for a short time and wait 5 seconds per attempt before removing it. Messages can be slower for a few seconds after someone leaves. The library's logs about this are hidden to keep the chat readable.

