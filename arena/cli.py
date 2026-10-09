import argparse
import asyncio
import json
from .store import Store
from .scheduler import submit
from .worker import work
from .export import export_bundle
from .resources import provenance


def main():
    parser = argparse.ArgumentParser(description="Agent Arena Local")
    parser.add_argument("--db", default="runtime/arena.sqlite")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("submit", "demo"):
        sub = commands.add_parser(command)
        sub.add_argument("--config", default="configs/simulated.json")
        sub.add_argument("--tasks", default="data/tasks.jsonl")
        if command == "demo":
            sub.add_argument("--output", required=True)
    worker = commands.add_parser("worker")
    worker.add_argument("--once", action="store_true", help="Drena la cola disponible y termina")
    export = commands.add_parser("export")
    export.add_argument("experiment_id")
    export.add_argument("--output", required=True)
    cancel = commands.add_parser("cancel")
    cancel.add_argument("run_id")
    commands.add_parser("status")
    commands.add_parser("hardware")
    commands.add_parser('create-test-user', help='Crea explícitamente la cuenta local de desarrollo test/test')
    recover = commands.add_parser("recover")
    recover.add_argument("--workers-stopped", action="store_true", required=True)
    args = parser.parse_args()
    store = Store(args.db)
    if args.command == 'create-test-user':
        from .accounts import Accounts
        Accounts(store).create_test_user()
        print('Cuenta local de desarrollo disponible: usuario test, contraseña test')
    elif args.command in {"submit", "demo"}:
        experiment_id = submit(store, args.config, args.tasks)
        print(experiment_id)
        if args.command == "demo":
            asyncio.run(work(store, once=True))
            export_bundle(store, experiment_id, args.output)
    elif args.command == "worker":
        asyncio.run(work(store, once=args.once))
    elif args.command == "export":
        export_bundle(store, args.experiment_id, args.output)
    elif args.command == "cancel":
        store.cancel(args.run_id)
    elif args.command == "recover":
        store.recover()
    elif args.command == "hardware":
        print(json.dumps(provenance(), indent=2))
    elif args.command == "status":
        print(json.dumps(store.list_runs(), indent=2))


if __name__ == "__main__":
    main()
