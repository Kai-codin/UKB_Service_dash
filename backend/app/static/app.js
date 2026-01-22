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
    const li = document.createElement('li'); li.className='list-group-item';
    li.innerHTML = `<strong>${s.name}</strong><br/><small>${s.base_path}</small>`;
    li.addEventListener('click', ()=> loadCommands(s.id));
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
      <button class='btn btn-sm btn-primary start'>Start</button>
      <button class='btn btn-sm btn-danger stop'>Stop</button>
      <button class='btn btn-sm btn-secondary viewlog'>View Log</button>
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
  }
}
