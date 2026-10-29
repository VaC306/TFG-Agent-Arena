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
    backup = commands.add_parser('backup',help='Copia consistente de toda la base local, incluidas cuentas')
    backup.add_argument('--output',required=True)
    restore = commands.add_parser('restore',help='Verifica y restaura a una base nueva; no sobrescribe datos')
    restore.add_argument('--source',required=True)
    restore.add_argument('--output',required=True)
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
    diagnostic = commands.add_parser('diagnose-tools', help='Comprueba herramientas aisladas y juntas con modelos reales')
    diagnostic.add_argument('--models', nargs='+', default=['qwen2.5:3b','qwen2.5:7b'])
    diagnostic.add_argument('--output', required=True)
    diagnostic.add_argument('--cases', default='benchmarks/v1/diagnostics/tool-calls.json')
    diagnostic.add_argument('--environment', default='benchmarks/v1/fixtures/orders.json')
    benchmark = commands.add_parser('benchmark', help='Ejecuta y audita datasets versionados en una base aislada')
    benchmark.add_argument('--root', default='benchmarks/v1')
    benchmark.add_argument('--output', required=True)
    benchmark.add_argument('--model-a', default='qwen2.5:3b')
    benchmark.add_argument('--model-b', default='qwen2.5:7b')
    benchmark.add_argument('--split', choices=['dev','eval'], default='dev')
    benchmark.add_argument('--suites', nargs='+', choices=['text','json','attachments','orders'], default=['text','json','attachments','orders'])
    benchmark.add_argument('--repetitions', type=int, default=1)
    recover = commands.add_parser("recover")
    recover.add_argument("--workers-stopped", action="store_true", required=True)
    args = parser.parse_args()
    store = Store(args.db) if args.command not in ('benchmark','diagnose-tools','backup','restore') else None
    if args.command in ('backup','restore'):
        from .backups import copy_database
        print(copy_database(args.source if args.command=='restore' else args.db,args.output,restore=args.command=='restore'))
    elif args.command == 'benchmark':
        from .benchmarks import run_benchmark
        asyncio.run(run_benchmark(args.root,args.output,args.model_a,args.model_b,args.split,args.suites,args.repetitions))
    elif args.command == 'diagnose-tools':
        from .diagnostics import diagnose_tools
        asyncio.run(diagnose_tools(args.models,args.output,args.cases,args.environment))
    elif args.command == 'create-test-user':
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
