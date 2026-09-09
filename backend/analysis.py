"""Released numeric routine: no model participates in the calculation."""
import math

def compare(a, b):
    if a['schema'] != 'ewb.series/1' or b['schema'] != 'ewb.series/1':
        raise ValueError('Unsupported export schema')
    if (a['x_unit'], a['y_unit']) != (b['x_unit'], b['y_unit']):
        raise ValueError('Input units do not match')
    pa,pb=a['points'],b['points']
    if len(pa)!=len(pb) or len(pa)<2: raise ValueError('Input lengths do not match')
    if any(x[0]!=y[0] for x,y in zip(pa,pb)): raise ValueError('Sample alignment failed')
    if not all(math.isfinite(v) for p in pa+pb for v in p): raise ValueError('Non-finite input')
    delta=[y[1]-x[1] for x,y in zip(pa,pb)]
    peak=max(range(len(delta)),key=lambda i:abs(delta[i]))
    return {'points_a':pa,'points_b':pb,'delta':[[pa[i][0],d] for i,d in enumerate(delta)],
            'metrics':{'samples':len(pa),'max_abs_delta':max(abs(v) for v in delta),
                       'rmse':math.sqrt(sum(v*v for v in delta)/len(delta)),
                       'mean_delta':sum(delta)/len(delta),'peak_sample':pa[peak][0]},
            'units':{'x':a['x_unit'],'y':a['y_unit']},
            'checks':[{'name':n,'passed':True} for n in ['Schema compatibility','Unit consistency','Sample alignment','Finite values']],
            'method':'analysis.compare_runs@1.0.0'}

DRAFT = '''# Proposed extension — human review required before execution.
# Inputs: reviewed C++ exports. No binary parser or network access.
import json
from pathlib import Path
inputs = json.loads(Path('/inputs/data.json').read_text())
a = inputs['a']['points']
b = inputs['b']['points']
# Five-sample moving average of the response difference.
delta = [y[1] - x[1] for x, y in zip(a, b)]
smoothed = []
for i in range(len(delta)):
    window = delta[max(0, i-2):min(len(delta), i+3)]
    smoothed.append([a[i][0], sum(window) / len(window)])
Path('/outputs/result.json').write_text(json.dumps({
    'extension': 'Five-sample moving-average difference',
    'points': smoothed,
    'unit': inputs['a']['y_unit']
}))
'''
