import pytest
from backend.scenes import validate_scene

def sample():return {'version':1,'title':'Box','units':'mm','objects':[{'type':'box','size':[2,3,4]}]}
def test_primitives_and_mesh():
    s=sample();s['objects'] += [{'type':'mesh','vertices':[[0,0,0],[1,0,0],[0,1,0]],'faces':[[0,1,2]]},{'type':'line','points':[[0,0,0],[1,1,1]]}]
    assert validate_scene(s)==s
@pytest.mark.parametrize('change',[{'url':'https://example.com'},{'size':[float('nan'),1,1]},{'size':[-1,1,1]},{'position':[True,0,0]},{'type':'script'},{'color':'url(x)'}])
def test_unsafe_geometry(change):
    s=sample();s['objects'][0].update(change)
    with pytest.raises(ValueError):validate_scene(s)
def test_invalid_mesh_and_budget():
    s=sample();s['objects']=[{'type':'mesh','vertices':[[0,0,0],[1,1,1]],'faces':[[0,1,5]]}]
    with pytest.raises(ValueError):validate_scene(s)
    s=sample();s['objects']*=101
    with pytest.raises(ValueError):validate_scene(s)


def test_standalone_scene_normalized_without_mutation():
    from backend.scenes import normalize_scene_output
    scene={'version':1,'title':'Example','units':'meters','objects':[{'type':'box','size':[1,2,3]}]}
    assert normalize_scene_output(scene)=={'scene3d':scene}
    assert 'scene3d' not in scene


def test_standalone_scene_rejects_quad_faces():
    from backend.scenes import normalize_scene_output
    import pytest
    scene={'version':1,'title':'Example','units':'meters','objects':[{'type':'mesh','vertices':[[0,0,0],[1,0,0],[1,1,0],[0,1,0]],'faces':[[0,1,2,3]]}]}
    with pytest.raises(ValueError):normalize_scene_output(scene)
