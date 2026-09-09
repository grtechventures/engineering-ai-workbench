import * as THREE from './vendor/three/three.module.min.js';
import {OrbitControls} from './vendor/three/OrbitControls.js';
const host=document.querySelector('#view'),status=document.querySelector('#status');
let renderer,controls;
try{
 const id=new URLSearchParams(location.search).get('task');
 if(id&&!/^[a-f0-9]{32}$/.test(id))throw Error('Invalid task reference');
 let data={version:1,title:'Sample bracket sketch',units:'illustrative units',objects:[{type:'box',size:[4,.3,2],color:'#358d94'},{type:'box',size:[.3,2,2],position:[-1.85,1,0],color:'#358d94'},{type:'sphere',radius:.25,position:[1,.5,0],color:'#d99836'}]};
 if(id){const r=await fetch('/api/python-tasks/'+id+'/scene');if(!r.ok)throw Error('Scene unavailable or invalid. Reopen the reviewed task.');data=await r.json()}
 document.querySelector('#title').textContent=data.title;
 const scene=new THREE.Scene();scene.background=new THREE.Color('#eef4f4');
 const camera=new THREE.PerspectiveCamera(45,1,.01,1000);
 renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));host.appendChild(renderer.domElement);
 controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=false;
 const group=new THREE.Group();scene.add(group);
 scene.add(new THREE.HemisphereLight(0xffffff,0x49616b,2));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(3,6,4);scene.add(light);
 for(const o of data.objects){let g,obj;const mat=new THREE.MeshStandardMaterial({color:o.color||'#5ab5ba',roughness:.65,side:THREE.DoubleSide});
  if(o.type==='box')g=new THREE.BoxGeometry(...o.size);
  else if(o.type==='sphere')g=new THREE.SphereGeometry(o.radius,24,16);
  else if(o.type==='cylinder')g=new THREE.CylinderGeometry(o.radius,o.radius,o.height,24);
  else if(o.type==='mesh'){g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(o.vertices.flat(),3));g.setIndex(o.faces.flat());g.computeVertexNormals()}
  else if(o.type==='line'){g=new THREE.BufferGeometry().setFromPoints(o.points.map(v=>new THREE.Vector3(...v)));obj=new THREE.Line(g,new THREE.LineBasicMaterial({color:o.color||'#358d94'}));mat.dispose()}
  else throw Error('Unsupported geometry');
  obj=obj||new THREE.Mesh(g,mat);obj.position.set(...(o.position||[0,0,0]));group.add(obj);
 }
 const bounds=new THREE.Box3().setFromObject(group),center=bounds.getCenter(new THREE.Vector3());let size=Math.max(bounds.getSize(new THREE.Vector3()).length(),.001);
 function draw(){renderer.render(scene,camera)}
 function reset(){camera.near=size/1000;camera.far=size*100;camera.position.copy(center).add(new THREE.Vector3(size,size*.7,size));controls.target.copy(center);camera.updateProjectionMatrix();controls.update();draw()}
 const axes=new THREE.AxesHelper(size*.6);axes.position.copy(center);scene.add(axes);
 const resize=new ResizeObserver(()=>{renderer.setSize(host.clientWidth,host.clientHeight);camera.aspect=host.clientWidth/host.clientHeight;camera.updateProjectionMatrix();draw()});resize.observe(host);
 controls.addEventListener('change',draw);document.querySelector('#reset').onclick=reset;
 document.querySelector('#export').onclick=()=>{draw();const a=document.createElement('a');a.href=renderer.domElement.toDataURL('image/png');a.download='workbench-3d.png';a.click()};
 status.textContent=`Units: ${data.units}. Drag to rotate; scroll to zoom; right-drag to pan. Review geometry and dimensions before engineering use.`;reset();
 addEventListener('pagehide',()=>{resize.disconnect();controls.dispose();scene.traverse(x=>{x.geometry?.dispose();x.material?.dispose?.()});renderer.dispose()},{once:true});
}catch(err){status.textContent='3D viewer unavailable: '+err.message;document.querySelector('#export').disabled=true;document.querySelector('#reset').disabled=true;controls?.dispose();renderer?.dispose()}
