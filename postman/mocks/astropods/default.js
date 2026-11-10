// Protocol fixture only: canned outputs do not simulate model intelligence.
const http = require('http');
http.createServer(async (req, res) => {
  const raw = req.body;
  const reply = (status, body) => {
    res.writeHead(status, {'Content-Type':'application/json'});
    res.end(JSON.stringify(body));
  };
  if (req.headers.authorization === 'Bearer denied-test-key') {
    return reply(403, {error: {message:'Test access denied', type:'permission_error', code:'forbidden'}});
  }
  let body;
  try { body = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch { return reply(400, {error:{message:'Invalid JSON'}}); }
  if (req.url === '/v1/embeddings' && req.method === 'POST') {
    if (!Array.isArray(body.input) || body.model !== 'titan-embed-text-v2') {
      return reply(400, {error:{message:'Unexpected embedding request'}});
    }
    return reply(200, {object:'list', model:body.model,
      data:body.input.map((_,index)=>({object:'embedding',index,embedding:[1,0]})),
      usage:{prompt_tokens:1,total_tokens:1}});
  }
  if (req.url === '/v1/chat/completions' && req.method === 'POST') {
    if (!body.messages || !body.model) return reply(400,{error:{message:'Missing fields'}});
    let payload = JSON.parse(body.messages[1].content);
    let output = {work_items:['Authentication']};
    if (payload.work_item) {
      const c = payload.sources[0];
      output = {description:'Authentication',category:'extra',quantity:'1',unit_price:'200',
        currency:'EUR',rationale:'Protocol fixture',price_approved:true,ready_to_invoice:true,
        conflicting_price:false,confidence:0.9,
        evidence:['price','approval','acceptance'].map(role=>({chunk_id:c.chunk_id,quote:c.text,role}))};
    }
    return reply(200,{id:'chatcmpl-fixture',object:'chat.completion',created:0,model:body.model,
      choices:[{index:0,finish_reason:'stop',message:{role:'assistant',content:JSON.stringify(output)}}]});
  }
  return reply(501,{error:{message:'Not covered by this protocol fixture'}});
}).listen(process.env.PORT || 4510);
