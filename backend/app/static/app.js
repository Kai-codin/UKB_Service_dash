let token = null;
let perms = "";

document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;
  const res = await fetch('/api/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username,password})});
  if (!res.ok) { alert('Login failed'); return; }
  const j = await res.json();
  token = j.token; perms = j.perms || '';
  document.getElementById('loginBox').style.display = 'none';
  document.getElementById('app').style.display = 'block';
  document.getElementById('me').innerText = username;
  loadSites();
});

document.getElementById('logout').addEventListener('click', () => {
  token = null; perms = '';
  document.getElementById('loginBox').style.display = '';
  document.getElementById('app').style.display = 'none';
});

async function loadSites(){
  const res = await fetch('/api/sites', {headers:{'Authorization':'Bearer '+token}});
  const sites = await res.json();
  const ul = document.getElementById('sites'); ul.innerHTML='';
  for(const s of sites){
    const li = document.createElement('li'); li.className='list-group-item d-flex justify-content-between align-items-start';
    const left = document.createElement('div');
    left.innerHTML = `<div><strong>${s.name}</strong></div><div class='small text-muted'>${s.base_path}</div>`;
    const right = document.createElement('div');
    const openBtn = document.createElement('button'); openBtn.className='btn btn-sm btn-link'; openBtn.innerText='Open';
    openBtn.addEventListener('click', ()=> loadCommands(s.id));
    const editBtn = document.createElement('button'); editBtn.className='btn btn-sm btn-link'; editBtn.innerText='Edit';
    editBtn.addEventListener('click', ()=> showEditSite(s));
    right.appendChild(openBtn); right.appendChild(editBtn);
    li.appendChild(left); li.appendChild(right);
    ul.appendChild(li);
  }
}

document.getElementById('addSiteForm').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const name = document.getElementById('siteName').value;
  const base_path = document.getElementById('sitePath').value;
  const base_command = document.getElementById('siteBaseCmd').value;
  await fetch('/api/sites', {method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+token}, body:JSON.stringify({name,base_path,base_command})});
  loadSites();
});

async function loadCommands(site_id){
  const res = await fetch(`/api/sites/${site_id}/commands`, {headers:{'Authorization':'Bearer '+token}});
  const cmds = await res.json();
  const container = document.getElementById('commands'); container.innerHTML='';
  const addForm = document.createElement('div');
  addForm.innerHTML = `
    <h5>Add Command</h5>
    <form id='addCmdForm'>
      <input id='cmdName' class='form-control mb-1' placeholder='name'>
      <input id='cmdTemplate' class='form-control mb-1' placeholder='command template e.g. python manage.py import_bods {api_key}'>
      <button class='btn btn-sm btn-success'>Add</button>
    </form>
    <hr>
  `;
  container.appendChild(addForm);
  document.getElementById('addCmdForm').addEventListener('submit', async (e)=>{
    e.preventDefault();
    const name = document.getElementById('cmdName').value;
    const command_template = document.getElementById('cmdTemplate').value;
    await fetch('/api/commands', {method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+token}, body:JSON.stringify({name,command_template,site_id})});
    loadCommands(site_id);
  });

  for(const c of cmds){
    const card = document.createElement('div'); card.className='card mb-2';
    card.innerHTML = `<div class='card-body'><h5>${c.name}</h5><pre>${c.command_template}</pre>
      <div class='btn-group mb-2' role='group'>
        <button class='btn btn-sm btn-primary start'>Start</button>
        <button class='btn btn-sm btn-danger stop'>Stop</button>
        <button class='btn btn-sm btn-secondary viewlog'>View Log</button>
        <button class='btn btn-sm btn-outline-secondary edit'>Edit</button>
      </div>
      <div class='editForm' style='display:none; border-top:1px solid #eee; padding-top:8px;'>
        <input class='form-control mb-1 editName' placeholder='name' />
        <input class='form-control mb-1 editTemplate' placeholder='command template' />
        <textarea class='form-control mb-1 editEnvs' placeholder='envs, one per line key=value'></textarea>
        <div><button class='btn btn-sm btn-success save'>Save</button> <button class='btn btn-sm btn-danger del'>Delete</button></div>
      </div>
      <div class='log mt-2' style='white-space:pre-wrap; background:#111; color:#0f0; padding:8px; display:none; max-height:300px; overflow:auto;'></div>
      </div>`;
    container.appendChild(card);
    card.querySelector('.start').addEventListener('click', async ()=>{
      await fetch(`/api/commands/${c.id}/start`, {method:'POST', headers:{'Authorization':'Bearer '+token}});
      alert('Started');
    });
    card.querySelector('.stop').addEventListener('click', async ()=>{
      await fetch(`/api/commands/${c.id}/stop`, {method:'POST', headers:{'Authorization':'Bearer '+token}});
      alert('Stopped');
    });
    card.querySelector('.viewlog').addEventListener('click', async ()=>{
      const r = await fetch(`/api/logs/${c.id}`, {headers:{'Authorization':'Bearer '+token}});
      const j = await r.json();
      const lbox = card.querySelector('.log');
      lbox.style.display = 'block';
      lbox.innerText = j.output || '(no output yet)';
    });
    card.querySelector('.edit').addEventListener('click', async ()=>{
      const form = card.querySelector('.editForm');
      const nameIn = card.querySelector('.editName');
      const tplIn = card.querySelector('.editTemplate');
      const envsIn = card.querySelector('.editEnvs');
      // load details
      const r = await fetch(`/api/commands/${c.id}`, {headers:{'Authorization':'Bearer '+token}});
      if (r.ok){
        const data = await r.json();
        nameIn.value = data.name || '';
        tplIn.value = data.command_template || '';
        envsIn.value = (data.envs || []).map(e=>`${e.key}=${e.value}`).join('\n');
        form.style.display = form.style.display==='none' ? 'block' : 'none';
      }
    });
    card.querySelector('.save').addEventListener('click', async ()=>{
      const form = card.querySelector('.editForm');
      const name = card.querySelector('.editName').value;
      const tpl = card.querySelector('.editTemplate').value;
      const envText = card.querySelector('.editEnvs').value.trim();
      const envs = envText ? envText.split('\n').map(l=>{const [k,...v]=l.split('='); return {key:k.trim(), value:v.join('=').trim()}}) : [];
      await fetch(`/api/commands/${c.id}`, {method:'PUT', headers:{'Content-Type':'application/json','Authorization':'Bearer '+token}, body:JSON.stringify({name,command_template:tpl,envs})});
      alert('Saved');
      form.style.display='none';
      loadCommands(c.site_id);
    });
    card.querySelector('.del').addEventListener('click', async ()=>{
      if (!confirm('Delete this command?')) return;
      await fetch(`/api/commands/${c.id}`, {method:'DELETE', headers:{'Authorization':'Bearer '+token}});
      loadCommands(c.site_id);
    });
  }
}

function showEditSite(s){
  // show a modal-like inline editor at top
  let box = document.getElementById('siteEditor');
  if (!box){
    box = document.createElement('div'); box.id='siteEditor'; box.className='mb-3'; document.querySelector('#app .container')?.prepend(box);
  }
  box.innerHTML = `
    <h5>Edit Site</h5>
    <input id='editSiteName' class='form-control mb-1' />
    <input id='editSitePath' class='form-control mb-1' />
    <input id='editSiteBaseCmd' class='form-control mb-1' />
    <div><button id='saveSite' class='btn btn-sm btn-success'>Save</button> <button id='delSite' class='btn btn-sm btn-danger'>Delete</button></div>
    <hr>
  `;
  document.getElementById('editSiteName').value = s.name || '';
  document.getElementById('editSitePath').value = s.base_path || '';
  document.getElementById('editSiteBaseCmd').value = s.base_command || '';
  document.getElementById('saveSite').addEventListener('click', async ()=>{
    const name = document.getElementById('editSiteName').value;
    const base_path = document.getElementById('editSitePath').value;
    const base_command = document.getElementById('editSiteBaseCmd').value;
    await fetch(`/api/sites/${s.id}`, {method:'PUT', headers:{'Content-Type':'application/json','Authorization':'Bearer '+token}, body:JSON.stringify({name,base_path,base_command})});
    loadSites();
  });
  document.getElementById('delSite').addEventListener('click', async ()=>{
    if (!confirm('Delete this site and its commands?')) return;
    await fetch(`/api/sites/${s.id}`, {method:'DELETE', headers:{'Authorization':'Bearer '+token}});
    loadSites();
  });
}
