"""Server-configured model boundary. No endpoint URLs or credentials from the browser."""
import os
from urllib.parse import urlparse
import httpx
from .network_policy import validate_model_url

class ModelGateway:
    def __init__(self):
        self.local_url=os.getenv('EWB_LOCAL_MODEL_URL','').rstrip('/')
        self.local_model=os.getenv('EWB_LOCAL_MODEL','')
        self.frontier_url=os.getenv('EWB_FRONTIER_URL','').rstrip('/')
        self.frontier_model=os.getenv('EWB_FRONTIER_MODEL','')
        self.frontier_key=os.getenv('EWB_FRONTIER_API_KEY','')
        if self.local_url:self.local_url=validate_model_url(self.local_url)

    def info(self):
        return {'local':{'configured':bool(self.local_url and self.local_model),'model':self.local_model or 'Deterministic demo'},
                'frontier':{'configured':False,'model':'Disabled by offline policy'},
                'boundary':'Internet model calls are disabled. Loopback is allowed; private LAN model IPs require explicit administrator approval.'}

    def complete(self, scope, prompt, *, engineering_context=None, schema=None):
        if scope=='frontier' and engineering_context is not None:
            raise ValueError('Engineering context cannot be sent to a frontier model')
        if scope=='frontier': raise ValueError('Internet inference is disabled by the offline policy')
        if scope=='local': url,model,key=validate_model_url(self.local_url) if self.local_url else '',self.local_model,os.getenv('EWB_LOCAL_API_KEY','')
        elif scope=='frontier': url,model,key=self.frontier_url,self.frontier_model,self.frontier_key
        else: raise ValueError('Unknown model scope')
        if not url or not model: raise ValueError('Model endpoint is not configured')
        headers={'Authorization':f'Bearer {key}'} if key else {}
        # OpenAI-compatible /v1 base URL, also supported by Ollama and many on-prem servers.
        messages=[{'role':'system','content':'Assist with engineering reasoning. Do not invent measurements. Responses are drafts requiring review.'},
                  {'role':'user','content':prompt}]
        if engineering_context is not None:
            messages.append({'role':'user','content':'Local authorized context: '+str(engineering_context)})
        payload={'model':model,'messages':messages,'temperature':0.1,'max_tokens':1500}
        if schema:
            payload['response_format']={'type':'json_schema','json_schema':{'name':'workbench_response','strict':True,'schema':schema}}
        try:
            with httpx.Client(timeout=120,trust_env=False,follow_redirects=False) as client:
                response=client.post(url+'/chat/completions',headers=headers,json=payload)
                response.raise_for_status()
                content=response.json()['choices'][0]['message']['content']
                if not isinstance(content,str) or not content.strip():raise ValueError('Empty response')
                return content[:16000]
        except (httpx.HTTPError,KeyError,IndexError,TypeError,ValueError) as exc:
            raise ValueError('The configured model did not return a usable response. Check that the model service is running, then retry. No alternative provider was contacted.') from exc

PUBLIC_PROMPTS={
    'rmse':'Explain root mean square error versus maximum absolute difference using only an invented numerical example. Do not request project data.',
    'validation':'Describe a general checklist for validating a numerical comparison method. Use no real project information.',
    'sampling':'Explain how sample alignment affects comparison of two synthetic response curves.'
}
