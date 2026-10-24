#!/usr/bin/env python3
"""Verify the saved CO2 MLPs and exact notebook functions on controlled inputs.

No original training is repeated, and no notebook, model or reported metric is
modified. Install in an isolated environment: tensorflow-cpu==2.21.0,
keras==3.13.2, numpy==2.3.5. Defaults are repository-relative notebooks/ and
outputs/models/. The three original .keras artifacts are required; --notebooks
and --models allow another local copy of those same inputs.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.metadata
import inspect
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import zipfile

# Bound resources before importing TensorFlow; settings apply only to this run.
for k, v in {
    'TF_CPP_MIN_LOG_LEVEL': '3', 'TF_ENABLE_ONEDNN_OPTS': '0',
    'CUDA_VISIBLE_DEVICES': '-1', 'OMP_NUM_THREADS': '1',
    'TF_NUM_INTRAOP_THREADS': '1', 'TF_NUM_INTEROP_THREADS': '1',
}.items():
    os.environ.setdefault(k, v)
if hasattr(os, 'sched_getaffinity'):
    original_affinity = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, original_affinity[:2])
else:
    original_affinity = None

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import keras as standalone_keras

tf.config.threading.set_inter_op_parallelism_threads(1)
tf.config.threading.set_intra_op_parallelism_threads(1)
tf.config.experimental.enable_op_determinism()

ROOT = next((p for p in Path(__file__).resolve().parents if (p/'notebooks').is_dir()), Path.cwd())
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--notebooks', type=Path, default=ROOT/'notebooks')
parser.add_argument('--reference-commit', default=None, help='Optional identity of the notebook version verified.')
parser.add_argument('--models', type=Path, default=ROOT/'outputs/models')
parser.add_argument('--output', type=Path, default=ROOT/'outputs/reproducibility/nn_verification.json')
parser.add_argument('--public-output', type=Path, help='Optional report using only repository-relative logical paths.')
args = parser.parse_args()
START = time.perf_counter()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def string_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def serial(value):
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    return value


SOURCE = {
 'backprop': {'reference': 'Rumelhart, Hinton e Williams (1986)',
             'location': 'pp. 533-534, equações (1)-(6), especialmente passe reverso na p. 534',
             'url': 'https://www.cs.toronto.edu/~hinton/absps/naturebp.pdf'},
 'relu': {'reference': 'Glorot, Bordes e Bengio (2011)',
          'location': 'p. 318, seção 3.1, rectifier(x)=max(0,x)',
          'url': 'https://proceedings.mlr.press/v15/glorot11a/glorot11a.pdf'},
 'adam': {'reference': 'Kingma e Ba (ICLR 2015), texto consultado arXiv v9, 30 jan. 2017',
          'location': 'p. 2, Algoritmo 1; forma eficiente com epsilon-hat imediatamente antes da seção 2.1',
          'url': 'https://arxiv.org/abs/1412.6980v9'},
 'keras_adam': {'reference': 'Keras 3.13.2, Adam',
                'location': 'API e implementação Adam.update_step, versão presente nos modelos preservados',
                'url': 'https://keras.io/api/optimizers/adam/'},
 'keras_es': {'reference': 'Keras 3.13.2, EarlyStopping',
              'location': 'min_delta, patience, on_epoch_end e on_train_end',
              'url': 'https://keras.io/api/callbacks/early_stopping/'},
 'keras_mse': {'reference': 'Keras 3.13.2, mean_squared_error',
               'location': 'redução mean(square(y_true-y_pred)), com compatibilização dos ranks',
               'url': 'https://keras.io/api/losses/regression_losses/'},
 'tf_grad': {'reference': 'TensorFlow, diferenciação automática e Keras TensorFlowTrainer.train_step',
             'location': 'GradientTape, tape.gradient(loss, trainable_weights), optimizer.apply_gradients',
             'url': 'https://www.tensorflow.org/guide/autodiff'},
}

NB_AB = '03A_modelagem_preditiva_co2.ipynb'
NB_C = '03A.01_modelagem_preditiva_co2.ipynb'
NB_DATA = {name: json.loads((args.notebooks/name).read_text()) for name in [NB_AB, NB_C]}
NB_HASH = {name: sha(args.notebooks/name) for name in NB_DATA}


def cell(name, number):
    c = NB_DATA[name]['cells'][number-1]
    assert c['cell_type'] == 'code'
    return ''.join(c['source'])


def extract_functions(name, number):
    source = cell(name, number)
    tree = ast.parse(source)
    allowed = {'LEARNING_RATE', 'BATCH_SIZE', 'MAX_EPOCHS', 'PATIENCE'}
    nodes = [n for n in tree.body if
             (isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) and t.id in allowed for t in n.targets))
             or (isinstance(n, ast.FunctionDef) and n.name in {'build_mlp', 'train_model'})]
    env = {'tf': tf, 'keras': keras, 'layers': layers, 'SEED': 42, 'np': np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), f'{name}:cell{number}', 'exec'), env)
    return env, tree


AB, AB_TREE = extract_functions(NB_AB, 12)
C, C_TREE = extract_functions(NB_C, 18)
CHECKS = []


def add_check(identifier, source_keys, code_cells, conditions, verification, result, passed=True):
    CHECKS.append({'id': identifier, 'sources': [SOURCE[k] for k in source_keys],
                   'code_cells_1based_including_markdown': code_cells,
                   'conditions': conditions, 'verification': verification,
                   'result': serial(result), 'passed': bool(passed)})
    print(identifier, 'PASS' if passed else 'FAIL', flush=True)
    assert passed, identifier


def forward_np(x, weights):
    w1,b1,w2,b2,w3,b3 = weights
    z1 = x @ w1 + b1
    h1 = np.maximum(z1, 0)
    z2 = h1 @ w2 + b2
    h2 = np.maximum(z2, 0)
    y = h2 @ w3 + b3
    return y, (z1,h1,z2,h2)


def loss_grad_np(x, y, weights):
    pred, (z1,h1,z2,h2) = forward_np(x, weights)
    target = np.asarray(y, dtype=np.float64).reshape(-1,1)
    n = len(target)
    loss = np.mean((pred-target)**2)
    dout = 2*(pred-target)/n
    w1,b1,w2,b2,w3,b3 = weights
    gw3 = h2.T @ dout
    gb3 = dout.sum(axis=0)
    dz2 = (dout @ w3.T)*(z2 > 0)
    gw2 = h1.T @ dz2
    gb2 = dz2.sum(axis=0)
    dz1 = (dz2 @ w2.T)*(z1 > 0)
    gw1 = x.T @ dz1
    gb1 = dz1.sum(axis=0)
    return float(loss), [gw1,gb1,gw2,gb2,gw3,gb3]


def finite_gradient_checks(x, y, weights, expected, rng):
    # Central differences of an independent NumPy scalar loss. Avoid ReLU kinks
    # by checking masks after both perturbations, not by assuming smoothness.
    target = np.asarray(y, dtype=np.float64).reshape(-1,1)
    _, cache = forward_np(x, weights)
    masks = [cache[0] > 0, cache[2] > 0]
    errors, samples, skipped = [], [], 0
    for layer_idx, w in enumerate(weights):
        candidates = rng.permutation(w.size)
        need = min(16, w.size)
        accepted = 0
        for flat_idx in candidates:
            coord = np.unravel_index(int(flat_idx), w.shape)
            before = w[coord]
            h = 1e-5*max(1.0, abs(before))
            compatible = False
            for _ in range(5):
                w[coord] = before+h
                plus, pc = forward_np(x, weights)
                w[coord] = before-h
                minus, mc = forward_np(x, weights)
                w[coord] = before
                compatible = all(np.array_equal(old, new > 0) for old,new in
                                 zip(masks+masks, [pc[0],pc[2],mc[0],mc[2]]))
                if compatible:
                    break
                h *= 0.1
            if not compatible:
                skipped += 1
                continue
            num = (np.mean((plus-target)**2)-np.mean((minus-target)**2))/(2*h)
            truth = expected[layer_idx][coord]
            err = abs(num-truth)
            errors.append(err)
            samples.append({'array':layer_idx, 'flat_index':int(flat_idx), 'central_difference':float(num),
                            'backprop_numpy':float(truth), 'step':float(h), 'absolute_error':float(err)})
            accepted += 1
            if accepted >= need:
                break
        assert accepted > 0
    return {'coordinates_checked':len(errors), 'kink_candidates_skipped':skipped,
            'max_absolute_error':max(errors), 'details':samples}


# Verify exact notebook builders and the serialized settings of the real models.
originals=[]
model_cases=[('A','03A_mlp_cenario_A.keras',1,2241,24),
             ('B','03A_mlp_cenario_B.keras',7,2625,38),
             ('C','03A01_mlp_cenario_C.keras',24,3713,57)]
rng=np.random.default_rng(20261024)
loaded_models=[]
for label, filename, dim, expected_params, reported_best in model_cases:
    path=args.models/filename
    before_hash=sha(path)
    with zipfile.ZipFile(path) as z:
        metadata=json.loads(z.read('metadata.json'))
        cfg=json.loads(z.read('config.json'))
    assert metadata['keras_version']=='3.13.2'
    model=keras.models.load_model(path)
    loaded_models.append(model)
    builder=AB['build_mlp'] if label in {'A','B'} else C['build_mlp']
    fresh=builder(dim)
    opt=model.optimizer.get_config()
    serialized=cfg['compile_config']['optimizer']['config']
    assert cfg['compile_config']['loss']=='mse'
    assert [l.units for l in model.layers]==[64,32,1]
    assert [l.activation.__name__ for l in model.layers]==['relu','relu','linear']
    assert model.count_params()==fresh.count_params()==expected_params
    assert (opt['beta_1'],opt['beta_2'],opt['epsilon'],opt['amsgrad'])==(0.9,0.999,1e-7,False)
    assert abs(opt['learning_rate']-1e-3)<1e-9
    assert fresh.optimizer.get_config()==opt
    # Original optimizer state records all performed minibatch updates.
    steps=int(model.optimizer.iterations.numpy())
    steps_per_epoch=math.ceil(4894/64)
    assert steps % steps_per_epoch == 0
    completed_epochs=steps//steps_per_epoch
    restored_epoch_implied=completed_epochs-30
    assert restored_epoch_implied==reported_best
    item={'scenario':label,'path':str(path),'sha256_before':before_hash,'metadata':metadata,
          'serialized_optimizer':serialized,'input_features':dim,'parameters':expected_params,
          'training_rows_from_saved_notebook_output':4894,'minibatches_per_epoch':steps_per_epoch,
          'saved_optimizer_iterations':steps,'completed_epochs_implied':completed_epochs,
          'selected_epoch_implied_by_patience':restored_epoch_implied,'reported_best_epoch':reported_best,
          'epoch_inference_conditions':'Um único fit por modelo; lote 64, 4.894 linhas, sem steps_per_epoch; parada antes de 500 épocas; EarlyStopping não restaura o estado do otimizador.'}
    weights=[w.astype(np.float64) for w in model.get_weights()]
    x=np.vstack([np.zeros(dim),np.ones(dim),np.full(dim,.5),np.linspace(.05,.95,dim),np.linspace(.95,.05,dim)]).astype('float32')
    if dim==1:
        x=np.array([[0],[.25],[.5],[.75],[1]],dtype='float32')
    keras_pred=model(x,training=False).numpy().astype(np.float64)
    numpy_pred,_=forward_np(x.astype(np.float64),weights)
    forward_error=float(np.max(np.abs(keras_pred-numpy_pred)))
    assert np.allclose(keras_pred,numpy_pred,atol=1e-6,rtol=3e-6)
    item['controlled_inputs']=x.tolist()
    item['tensorflow_predictions']=keras_pred.tolist()
    item['numpy_predictions']=numpy_pred.tolist()
    item['forward_max_absolute_error']=forward_error
    # Independent gradients at the original saved weights.
    gx=rng.uniform(.07,.93,size=(5,dim)).astype('float32')
    gy=np.linspace(.13,.87,5).astype('float32')
    with tf.GradientTape() as tape:
        pred=model(gx,training=True)
        loss=model.compute_loss(x=gx,y=gy,y_pred=pred,training=True)
    gradients=tape.gradient(loss,model.trainable_weights)
    assert all(g is not None for g in gradients)
    tf_grads=[g.numpy().astype(np.float64) for g in gradients]
    np_loss,np_grads=loss_grad_np(gx.astype(np.float64),gy,weights)
    flat_tf=np.concatenate([g.ravel() for g in tf_grads])
    flat_np=np.concatenate([g.ravel() for g in np_grads])
    assert np.allclose(flat_tf,flat_np,atol=5e-6,rtol=3e-5)
    loss_2d=float(model.compute_loss(x=gx,y=gy.reshape(-1,1),y_pred=pred,training=True).numpy())
    assert abs(float(loss.numpy())-np_loss)<1e-6
    assert abs(float(loss.numpy())-loss_2d)<1e-8
    finite=finite_gradient_checks(gx.astype(np.float64),gy,weights,np_grads,rng)
    assert finite['max_absolute_error']<2e-7
    item['gradient_verification']={'parameters_compared':int(flat_np.size),
        'mse_tensorflow':float(loss.numpy()),'mse_numpy':np_loss,
        'flat_vs_column_target_mse_difference':abs(float(loss.numpy())-loss_2d),
        'max_absolute_autodiff_vs_independent_backprop_error':float(np.max(np.abs(flat_tf-flat_np))),
        'relative_l2_gradient_error':float(np.linalg.norm(flat_tf-flat_np)/max(np.linalg.norm(flat_np),1e-15)),
        'central_difference':finite}
    item['sha256_after']=sha(path)
    assert item['sha256_after']==before_hash
    originals.append(item)
    print('original_model_'+label,'PASS',flush=True)

add_check('saved_models_and_real_builders',['relu','backprop','adam','keras_adam'],
          [{'notebook':NB_AB,'cells':[9,12,13,21]},{'notebook':NB_C,'cells':[16,18,19,31]}],
          'Pesos originais carregados sem alteração; entradas 1/7/24; camadas 64-ReLU, 32-ReLU, 1-linear; float32; MSE; Adam sem regularização adicional, AMSGrad ou clipping.',
          'Executar as duas funções build_mlp extraídas por AST; confrontar os modelos salvos e configurações; comparar cinco previsões por modelo com multiplicação matricial e max(0,z) independentes em NumPy.',
          {'models':originals,'saved_files_unchanged':True})
add_check('backprop_mse_and_finite_differences',['backprop','relu','keras_mse','tf_grad'],
          [{'notebook':NB_AB,'cells':[12,13]},{'notebook':NB_C,'cells':[18,19]}],
          'Perda escalar MSE=mean((pred-y)^2); gradiente de saída 2(pred-y)/n; derivada ReLU 1 para z>0 e 0 para z<0. Diferenças finitas somente onde os padrões de ativação não mudam.',
          'Comparar todos os gradientes de GradientTape/compute_loss com retropropagação NumPy independente, e uma amostra por tensor com diferenças centrais. Conferir y achatado, como nos notebooks, contra y em coluna.',
          {'parameters_compared':sum(x['gradient_verification']['parameters_compared'] for x in originals),
           'finite_difference_coordinates':sum(x['gradient_verification']['central_difference']['coordinates_checked'] for x in originals),
           'max_autodiff_error':max(x['gradient_verification']['max_absolute_autodiff_vs_independent_backprop_error'] for x in originals),
           'max_finite_difference_error':max(x['gradient_verification']['central_difference']['max_absolute_error'] for x in originals),
           'meaning_of_original_loss_scaling':'A soma com fator 1/2 da derivação de 1986 e o MSE médio diferem por uma constante positiva. A regra da cadeia é a mesma; o teste verifica o fator 2/n efetivamente usado, sem supor gradientes numericamente idênticos entre essas perdas.'})

# Check the nonsmooth boundary explicitly rather than treating it as a failed gradient.
xv=tf.Variable([-3.,-1e-8,0.,1e-8,2.],dtype=tf.float32)
with tf.GradientTape() as tape:
    rv=keras.activations.relu(xv)
    rs=tf.reduce_sum(rv)
rg=tape.gradient(rs,xv).numpy()
assert np.array_equal(rv.numpy(),np.maximum(xv.numpy(),0))
assert np.array_equal(rg,np.array([0,0,0,1,1]))
add_check('relu_boundary_convention',['relu','tf_grad'],
          [{'notebook':NB_AB,'cells':[12]},{'notebook':NB_C,'cells':[18]}],
          'ReLU não é diferenciável em zero; TensorFlow adota gradiente zero nesse ponto.',
          'Avaliar ativação e gradiente em valores negativos, zero e positivos.',
          {'inputs':xv.numpy(),'outputs':rv.numpy(),'gradients':rg,'assessment':'Convenção válida e explícita; não é erro de retropropagação.'})

# Independently verify Adam moments, bias correction and epsilon placement.
adam_config=loaded_models[0].optimizer.get_config()
adam=keras.optimizers.Adam.from_config(adam_config)
initial=np.array([.8,-.4,1e-4,-1e-4,.2,1.7],dtype='float32')
variable=tf.Variable(initial)
seq=np.array([[.1,-.2,0,1e-10,-1e-8,4.],
              [.05,.1,0,-2e-10,2e-8,-2.],
              [-.2,.05,0,1e-9,-3e-8,.1]],dtype='float32')
m=np.zeros(6,dtype=np.float64);v=m.copy()
ref=initial.astype(np.float64);canonical=ref.copy();fixed_algorithm1=ref.copy()
b1,b2,eps=adam_config['beta_1'],adam_config['beta_2'],adam_config['epsilon']
lr=adam_config['learning_rate'];adam_steps=[]
for t,g32 in enumerate(seq,1):
    g=g32.astype(np.float64)
    m=b1*m+(1-b1)*g
    v=b2*v+(1-b2)*g*g
    alpha=lr*np.sqrt(1-b2**t)/(1-b1**t)
    ref-=alpha*m/(np.sqrt(v)+eps)
    epsilon_t=eps/np.sqrt(1-b2**t)
    canonical-=lr*(m/(1-b1**t))/(np.sqrt(v/(1-b2**t))+epsilon_t)
    fixed_algorithm1-=lr*(m/(1-b1**t))/(np.sqrt(v/(1-b2**t))+1e-8)
    adam.apply_gradients([(tf.convert_to_tensor(g32),variable)])
    actual=variable.numpy().astype(np.float64)
    actual_m=adam._momentums[0].numpy().astype(np.float64)
    actual_v=adam._velocities[0].numpy().astype(np.float64)
    assert np.allclose(actual_m,m,atol=1e-12,rtol=2e-6)
    assert np.allclose(actual_v,v,atol=1e-16,rtol=2e-6)
    error=float(np.max(np.abs(actual-ref)))
    assert error<2e-7
    assert np.allclose(canonical,ref,atol=1e-15,rtol=1e-15)
    assert actual[2]==float(initial[2])
    adam_steps.append({'step':t,'gradient':g32,'actual':actual,'independent_epsilon_hat_form':ref.copy(),
                       'max_absolute_error':error,
                       'first_moment_max_absolute_error':float(np.max(np.abs(actual_m-m))),
                       'second_moment_max_absolute_error':float(np.max(np.abs(actual_v-v))),
                       'epsilon_algorithm1_for_exact_algebraic_equivalence':epsilon_t})
add_check('adam_update_equation',['adam','keras_adam'],
          [{'notebook':NB_AB,'cells':[12]},{'notebook':NB_C,'cells':[18]}],
          'Configuração lida dos três arquivos .keras: lr≈0,001, beta1=0,9, beta2=0,999, epsilon-hat=1e-7, amsgrad=False. Vetores incluem gradiente zero, troca de sinal e valores menores que epsilon.',
          'Executar três apply_gradients no Adam real de Keras 3.13.2, confrontando momentos e atualização com fórmula NumPy da p. 2, antes da seção 2.1. Confrontar também a equivalência algébrica com epsilon_t ajustado.',
          {'optimizer_config':adam_config,'steps':adam_steps,
           'max_absolute_error':max(x['max_absolute_error'] for x in adam_steps),
           'difference_from_algorithm1_fixed_epsilon_1e_8':float(np.max(np.abs(ref-fixed_algorithm1))),
           'assessment':'Implementação correta da forma eficiente descrita na própria fonte. Epsilon-hat constante 1e-7 não é o epsilon constante 1e-8 do Algoritmo 1; essa parametrização documentada não é erro. Não se alterou o epsilon dos modelos.'})

# Original EarlyStopping expressions, including min_delta and patience.
def get_callback_from_notebook(name, number, within_function=False):
    tree=ast.parse(cell(name,number))
    body=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='train_model').body if within_function else tree.body
    node=next(n for n in body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='early_stopping' for t in n.targets))
    env=dict(AB if within_function else C)
    exec(compile(ast.Module(body=[node],type_ignores=[]),f'{name}:callback','exec'),env)
    return env['early_stopping']

cb=get_callback_from_notebook(NB_AB,12,True)
cb_c=get_callback_from_notebook(NB_C,19)
assert cb.monitor==cb_c.monitor=='val_loss'
assert cb.patience==cb_c.patience==30
assert cb.min_delta==cb_c.min_delta==1e-6
assert cb.restore_best_weights and cb_c.restore_best_weights
probe=keras.Sequential([keras.layers.Input((1,)),keras.layers.Dense(1,kernel_initializer='zeros',bias_initializer='zeros')])
probe.stop_training=False
cb.set_model(probe);cb.on_train_begin()
sequence=[1e-2,1e-2-5e-7,1e-2-2e-6]+[1e-2-2e-6]*30
states=[]
for epoch,value in enumerate(sequence):
    probe.set_weights([np.zeros((1,1),dtype='float32'),np.array([epoch],dtype='float32')])
    cb.on_epoch_end(epoch,{'val_loss':value})
    states.append({'epoch_1based':epoch+1,'val_loss':value,'best_epoch_1based':cb.best_epoch+1,'wait':cb.wait})
    if probe.stop_training:
        break
cb.on_train_end()
assert states[1]['best_epoch_1based']==1
assert states[2]['best_epoch_1based']==3
assert len(states)==33 and cb.best_epoch+1==3
assert float(probe.get_weights()[-1][0])==2
add_check('early_stopping_delta_patience_restore',['keras_es'],
          [{'notebook':NB_AB,'cells':[12]},{'notebook':NB_C,'cells':[19]}],
          'monitor=val_loss, mode=auto resolve minimização, min_delta=1e-6, patience=30, restore_best_weights=True.',
          'Executar o callback da expressão original com sequência controlada: queda de 5e-7 ignorada, queda de 2e-6 aceita, depois 30 épocas sem melhoria; pesos sentinela distintos por época.',
          {'states':states,'stopped_epoch_1based':cb.stopped_epoch+1,'restored_epoch_1based':cb.best_epoch+1,
           'restored_sentinel_bias':float(probe.get_weights()[-1][0]),
           'assessment':'Minimização, tolerância, paciência e restauração operam conforme configurado. A seleção respeita min_delta; não é definida como todo mínimo numérico de val_loss.'})

# Exercise the real A/B training function and the real inline C training call on
# four zero inputs. Training target +1 and validation target -1 make validation
# strictly worse after the first update. All original training settings remain.
fit_cases=[]
for name,dim,env in [('AB',1,AB),('C',24,C)]:
    initial_model=env['build_mlp'](dim)
    expected=[w.copy() for w in initial_model.get_weights()]
    x=np.zeros((4,dim),dtype='float32')
    y=np.ones(4,dtype='float32')
    vy=-np.ones(4,dtype='float32')
    # Independent first Adam update: with zero inputs/biases, only output bias
    # has a nonzero derivative, dMSE/db=-2. The best checkpoint is epoch one.
    grad=-2.0
    m1=(1-.9)*grad;v1=(1-.999)*grad*grad
    eta=float(initial_model.optimizer.learning_rate.numpy())*np.sqrt(1-.999)/(1-.9)
    expected[-1]=expected[-1]+(-eta*m1/(np.sqrt(v1)+1e-7))
    if name=='AB':
        trained,history=env['train_model'](x,y,x,vy,dim)
    else:
        run=dict(env)
        run.update({'model_C':env['build_mlp'](dim),'X_train_C_scaled':x,'y_train_scaled':y,
                    'X_validation_C_scaled':x,'y_validation_scaled':vy})
        tree=ast.parse(cell(NB_C,19))
        selected=[n for n in tree.body if isinstance(n,ast.Assign) and any(
                    isinstance(t,ast.Name) and t.id in {'early_stopping','history_C'} for t in n.targets)]
        exec(compile(ast.Module(body=selected,type_ignores=[]),f'{NB_C}:cell19-fit','exec'),run)
        trained,history=run['model_C'],run['history_C']
    count=len(history.history['val_loss'])
    max_error=max(float(np.max(np.abs(g.astype('float64')-w.astype('float64')))) for g,w in zip(trained.get_weights(),expected))
    assert count==31
    assert np.argmin(history.history['val_loss'])==0
    assert np.all(np.diff(history.history['val_loss'])>0)
    assert max_error<2e-8
    fit_cases.append({'case':name,'synthetic_training_rows':4,'synthetic_validation_rows':4,
                      'original_max_epochs':env['MAX_EPOCHS'],'original_patience':env['PATIENCE'],
                      'epochs_actually_run':count,'selected_epoch':1,
                      'returned_weights_vs_independent_epoch1_max_error':max_error,
                      'first_val_loss':history.history['val_loss'][0],
                      'last_val_loss_before_restoration':history.history['val_loss'][-1]})
    print('real_train_path_'+name,'PASS',flush=True)
add_check('real_notebook_training_paths',['backprop','adam','keras_es'],
          [{'notebook':NB_AB,'cells':[12,13]},{'notebook':NB_C,'cells':[18,19]}],
          'Função train_model e chamada model_C.fit extraídas sem modificar hiperparâmetros; quatro observações sintéticas; validação distinta e sem acesso ao teste.',
          'Executar ambos os caminhos até a parada antecipada previsível, e comparar todos os pesos retornados com o primeiro passo Adam calculado independentemente. Não usar dados originais para treinamento.',
          {'cases':fit_cases,'total_synthetic_epochs':sum(v['epochs_actually_run'] for v in fit_cases),
           'assessment':'O treinamento real dos notebooks encaminha gradientes e parâmetros corretamente e retorna os pesos da época selecionada, não os da última época executada.'})

# Record actual implementation sources and preserve original files.
objects={'Adam.update_step':keras.optimizers.Adam.update_step,
         'EarlyStopping.on_epoch_end':keras.callbacks.EarlyStopping.on_epoch_end,
         'EarlyStopping.on_train_end':keras.callbacks.EarlyStopping.on_train_end,
         'mean_squared_error':standalone_keras.losses.mean_squared_error}
from keras.src.backend.tensorflow.trainer import TensorFlowTrainer
objects['TensorFlowTrainer.train_step']=TensorFlowTrainer.train_step
implementation=[]
for name,obj in objects.items():
    path=Path(inspect.getsourcefile(obj))
    src,first=inspect.getsourcelines(obj)
    implementation.append({'object':name,'file':str(path),'first_line':first,
                           'last_line':first+len(src)-1,'file_sha256':sha(path),
                           'excerpt_sha256':string_sha(''.join(src))})
for item in originals:
    assert sha(item['path'])==item['sha256_before']
for name,h in NB_HASH.items():
    assert sha(args.notebooks/name)==h

audit={
 'decision':'método aplicado corretamente no escopo declarado',
 'scope':'MLP dos cenários A/B/C: arquitetura, forward com pesos originais, MSE, retropropagação, ReLU, Adam, parada antecipada e restauração. Não foi repetido treinamento integral nem alteradas métricas publicadas.',
 'environment':{'python':platform.python_version(),'python_executable':sys.executable,
    'tensorflow':tf.__version__,'tensorflow_distribution':'tensorflow-cpu',
    'keras':standalone_keras.__version__,'numpy':np.__version__,
    'keras_version_saved_in_all_original_models':'3.13.2',
    'tensorflow_version_provenance':'2.21.0 consta do ambiente documentado de reprodução; arquivos .keras originais registram Keras 3.13.2, mas não a versão TensorFlow do salvamento.',
    'old_environment_attempt':'O runtime principal não possuía TensorFlow. O venv de reprodução antigo importou NumPy, mas TensorFlow abortou com SIGBUS no carregamento de _pywrap_cpu_feature_guard. Criado ambiente isolado, sem alterar o repositório ou seus locks.',
    'platform':platform.platform(),'devices':[d.name for d in tf.config.list_physical_devices()],
    'cpu_affinity':sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
    'packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions()}},
 'notebook_commit':args.reference_commit,
 'notebooks':[{'path':str(args.notebooks/name),'sha256':h} for name,h in NB_HASH.items()],
 'cell_counting':'1-based, incluindo Markdown; não é execution_count.',
 'sources':SOURCE,'library_implementation':implementation,'checks':CHECKS,
 'equivalent_or_compatible_differences':[
    {'difference':'MSE médio em lugar da soma de erros quadráticos com fator 1/2 na derivação de 1986',
     'classification':'Escala distinta do objetivo, regra da cadeia corretamente aplicada',
     'evidence':'Gradiente 2(pred-y)/n confrontado para todos os 8.579 parâmetros com diferenciação automática e diferenças finitas.'},
    {'difference':'ReLU em lugar das unidades logísticas do exemplo de retropropagação de 1986',
     'classification':'Composição válida com a ativação fundamentada em Glorot et al.; convenção zero em z=0',
     'evidence':'Forward dos modelos salvos, máscaras de ativação, derivadas e pontos de não diferenciabilidade verificados.'},
    {'difference':'epsilon-hat=1e-7 na forma eficiente de Adam, em lugar do epsilon=1e-8 constante do Algoritmo 1',
     'classification':'Parametrização prevista no texto de Kingma e Ba e documentada no Keras, não erro',
     'evidence':'Configuração original salva e três atualizações numéricas confrontadas. Equivalência algébrica exige epsilon_t=epsilon_hat/sqrt(1-beta2^t).'},
    {'difference':'Arquitetura 64/32, batch 64, paciência 30, min_delta=1e-6 e períodos de treino/validação',
     'classification':'Escolhas próprias coerentes com o uso declarado; não são prescrições dos artigos fundadores',
     'evidence':'Código e arquivos salvos concordam; o mecanismo de seleção foi executado em casos controlados.'}],
 'concrete_errors_found':[],
 'patches_required':[],
 'checkpoint_reporting':{'assessment':'Os contadores de Adam salvos corroboram 54/68/87 épocas executadas com 77 lotes por época. Descontada a paciência 30, as épocas selecionadas inferidas são 24/38/57, iguais às informadas. Não há fundamento para alterar esses números.',
    'precision':'Com min_delta>0, seleção do callback e argmin numérico não são sinônimos em qualquer sequência; aqui os contadores preservados e a regra executada corroboram os números publicados.'},
 'original_files_unchanged':True,'full_training_reexecuted':False,
 'elapsed_seconds':round(time.perf_counter()-START,3)
}
audit['summary']={
 'checks_passed':len(CHECKS),'models_checked':len(originals),
 'parameters_checked':sum(x['gradient_verification']['parameters_compared'] for x in originals),
 'finite_difference_coordinates':sum(x['gradient_verification']['central_difference']['coordinates_checked'] for x in originals),
 'max_prediction_error':max(x['forward_max_absolute_error'] for x in originals),
 'prediction_error_units':'escala normalizada da saída; diferença entre implementações, não erro preditivo em short tons',
 'max_autodiff_error':max(x['gradient_verification']['max_absolute_autodiff_vs_independent_backprop_error'] for x in originals),
 'max_central_difference_error':max(x['gradient_verification']['central_difference']['max_absolute_error'] for x in originals),
 'max_adam_update_error':max(x['max_absolute_error'] for x in adam_steps),
 'max_restored_weight_error':max(x['returned_weights_vs_independent_epoch1_max_error'] for x in fit_cases),
 'by_model':[{'scenario':x['scenario'],'parameters_checked':x['gradient_verification']['parameters_compared'],
              'prediction_max_absolute_error':x['forward_max_absolute_error'],
              'autodiff_max_absolute_error':x['gradient_verification']['max_absolute_autodiff_vs_independent_backprop_error'],
              'finite_difference_coordinates':x['gradient_verification']['central_difference']['coordinates_checked'],
              'finite_difference_max_absolute_error':x['gradient_verification']['central_difference']['max_absolute_error'],
              'saved_optimizer_steps':x['saved_optimizer_iterations'],
              'selected_epoch_corroborated':x['selected_epoch_implied_by_patience']} for x in originals]
}
audit['required_packages']={'tensorflow-cpu':'2.21.0','keras':'3.13.2','numpy':'2.3.5'}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(serial(audit),ensure_ascii=False,indent=2,allow_nan=False)+'\n')
if args.public_output:
    public=json.loads(json.dumps(serial(audit),ensure_ascii=False,allow_nan=False))
    public['environment'].pop('python_executable',None)
    for n in public['notebooks']:
        n['path']='notebooks/'+Path(n['path']).name
    for check in public['checks']:
        for model in check['result'].get('models',[]):
            model['path']='outputs/models/'+Path(model['path']).name
    for impl in public['library_implementation']:
        impl['file']=impl['file'].split('/site-packages/')[-1]
    public['path_convention']='Caminhos lógicos relativos ao repositório; --models permite apontar para os mesmos três artefatos preservados em outro diretório.'
    encoded=json.dumps(public,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    assert not any(p in encoded for p in ['/workspace/','/tmp/','/home/','/root/'])
    args.public_output.parent.mkdir(parents=True,exist_ok=True)
    args.public_output.write_text(encoded)
print(json.dumps({'decision':audit['decision'],'checks':len(CHECKS),'models':len(originals),
                  'max_forward_error':max(v['forward_max_absolute_error'] for v in originals),
                  'gradient_parameters':sum(v['gradient_verification']['parameters_compared'] for v in originals),
                  'finite_difference_coordinates':sum(v['gradient_verification']['central_difference']['coordinates_checked'] for v in originals),
                  'output':str(args.output),'seconds':audit['elapsed_seconds']},ensure_ascii=False),flush=True)
