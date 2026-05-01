let chart;

async function runTest(){

 const body = {
   message: document.getElementById("message").value,
   model: document.getElementById("model").value,
   top_k: parseInt(document.getElementById("topk").value),
   rag: document.getElementById("rag").checked
 };

 const res = await fetch("/chat",{
   method:"POST",
   headers:{ "Content-Type":"application/json" },
   body: JSON.stringify(body)
 });

 const d = await res.json();

 document.getElementById("reply").textContent = d.reply;

 document.getElementById("metrics").innerHTML = `
 Time: ${d.time_taken}s<br>
 Prompt Tokens: ${d.prompt_tokens}<br>
 Output Tokens: ${d.output_tokens}<br>
 Speed: ${d.tokens_per_sec} tok/s<br>
 Context Tokens: ${d.context_tokens}<br>
 `;

 loadHistory();
}

async function loadHistory(){

 const res = await fetch("/history");
 const rows = await res.json();

 let html = `
 <tr>
 <th>ID</th><th>Model</th><th>RAG</th>
 <th>Time</th><th>Prompt</th><th>Output</th><th>Speed</th>
 </tr>`;

 let labels = [];
 let vals = [];

 rows.reverse().forEach(r=>{
   html += `
   <tr>
   <td>${r[0]}</td>
   <td>${r[2]}</td>
   <td>${r[3]}</td>
   <td>${r[5]}</td>
   <td>${r[6]}</td>
   <td>${r[7]}</td>
   <td>${r[8]}</td>
   </tr>
   `;

   labels.push(r[0]);
   vals.push(r[8]);
 });

 document.getElementById("history").innerHTML = html;

 if(chart) chart.destroy();

 chart = new Chart(document.getElementById("chart"),{
   type:'line',
   data:{
     labels:labels,
     datasets:[{
       label:'Tokens/sec',
       data:vals
     }]
   }
 });
}

loadHistory();