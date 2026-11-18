
import argparse
import asyncio
import json
import logging

from kademlia.network import Server

# Hide the library's routine network logs (e.g. "no response from ..." when a peer leaves).
logging.getLogger("kademlia").setLevel(logging.CRITICAL)
logging.getLogger("rpcudp").setLevel(logging.CRITICAL)

node = Server()  
current_user = None  
chat_seen = 0  # how many global chat messages we've already shown


async def get(key, default):
    # Look up a key in the DHT. Returns default if nobody has stored it yet.
    raw = await node.get(key)
    return json.loads(raw) if raw is not None else default

async def put(key, value):
    # Store a value in the DHT. It gets copied to the nodes closest to the key.
    await node.set(key, json.dumps(value))

async def append(key, item):
    # Read the list, add one item, write the whole list back (read-modify-write).
    items = await get(key, [])
    items.append(item)
    await put(key, items)

async def ask(prompt):
    return await asyncio.to_thread(input, prompt)

async def show_new(key, seen, label):
    # Print messages after position `seen` in a list, and return the new position.
    messages = await get(key, [])
    for m in messages[seen:]:
        if m["from"] != current_user:  # don't echo messages back
            print(f"\n[{label}] {m['from']}: {m['text']}")
    return len(messages)


async def receive():
    # Runs forever alongside the prompt, checking for new messages every 2 seconds.
    global chat_seen
    while True:
        chat_seen = await show_new("chat", chat_seen, "all")
        dm_seen = await get(f"seen:{current_user}", 0)
        new_dm_seen = await show_new(f"inbox:{current_user}", dm_seen, "DM")
        if new_dm_seen > dm_seen:
            await put(f"seen:{current_user}", new_dm_seen)

        await asyncio.sleep(2)

HELP = """Type a message and press Enter to send it to everyone.
  /dm <name> <message>   private message (delivered even if they're offline)
  /users                 list everyone who has joined
  /help                  show this list again
  /quit                  exit"""

async def chat():
    print(HELP)
    while True:
        line = (await ask("> ")).strip()
        if line == "/quit":
            return
        if line.startswith("/dm "):
            parts = line.split(maxsplit=2)  #splits messages
            if len(parts) < 3:
                print("Usage: /dm <name> <message>")
                continue
            await append(f"inbox:{parts[1]}", {"from": current_user, "text": parts[2]})
        elif line == "/help":
            print(HELP)
        elif line == "/users":
            print("Users:", ", ".join(await get("users", [])))
        elif line:
            await append("chat", {"from": current_user, "text": line})

def ignore_shutdown_noise(loop, context):
    if not isinstance(context.get("exception"), asyncio.InvalidStateError):
        loop.default_exception_handler(context)


async def main():
    global current_user, chat_seen
    asyncio.get_running_loop().set_exception_handler(ignore_shutdown_noise)
    parser = argparse.ArgumentParser(description="conf-chat P2P node")
    parser.add_argument("--port", type=int, default=8468)
    parser.add_argument("--bootstrap", help="host:port of any running node")
    parser.add_argument("--relay", action="store_true", help="run a node with no chat prompt")
    args = parser.parse_args()

    await node.listen(args.port)
    if args.bootstrap:
        host, port = args.bootstrap.split(":")
        found = await node.bootstrap([(host, int(port))])  # join the network through a known peer
        if not found:
            print(f"Couldn't reach a node at {args.bootstrap}. Is it running? Start it first.")
            node.stop()
            return

    if args.relay:
        print(f"Node running on port {args.port}. Press Ctrl+C to stop.")
        await asyncio.Event().wait()  # wait forever
    else:
        while not current_user:
            current_user = (await ask("Your name: ")).strip()
        if current_user not in await get("users", []):
            await append("users", current_user)  # add ourselves to the user list once
        chat_seen = len(await get("chat", []))  # only show global messages sent after joining
        asyncio.create_task(receive())
        await chat()
    node.stop()


if __name__ == "__main__":
    asyncio.run(main())
