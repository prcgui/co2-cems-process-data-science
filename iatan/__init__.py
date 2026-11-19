"""Experimentos de estimação contemporânea de CO2 em Iatan 2."""
import json
import os

# O contexto publicado identifica a equipe e o pacote, sem herdar usuário,
# caminho do executável, repositório local ou identificadores de uma sessão.
try:
    _context = json.loads(os.environ.get('MLFLOW_RUN_CONTEXT', '{}'))
except (TypeError, ValueError):
    _context = {}
if not isinstance(_context, dict):
    _context = {}
PUBLIC_CONTEXT = {
    'mlflow.user': 'equipe',
    'mlflow.source.name': 'iatan',
    'mlflow.source.type': 'LOCAL',
    'mlflow.source.git.commit': '',
    'mlflow.source.git.branch': '',
    'mlflow.source.git.repoURL': '',
    'mlflow.source.git.diff': '',
    'mlflow.source.git.dirty': '',
}
_context.update(PUBLIC_CONTEXT)
os.environ['MLFLOW_RUN_CONTEXT'] = json.dumps(_context)
# Evita avisos opcionais de importação contendo a localização da instalação.
os.environ['MLFLOW_DISABLE_AGENT_HINT'] = '1'
del _context
