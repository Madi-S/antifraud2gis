


document.getElementById('search-formQQQ').addEventListener('submit', function(e) {
    e.preventDefault();
    const OID = document.getElementById('oid').value;
    const resultContainer = document.getElementById('result-container');
    
    console.log("search", OID)

    fetch("/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ oid: OID }),
      })
        .then(response => response.json())
        .then(data => {
            console.log(data.relations);
            const resultDiv = document.getElementById("result");
                       
            // Create table for relations
            let tableHTML = `
                <table>
                    <thead>
                        <tr>
                            <th>Title</th>
                            <th>Town</th>
                            <th>Hits</th>
                            <th>Median</th>
                            <th>A/B rating</th>                            
                        </tr>
                    </thead>
                    <tbody>
            `;

            data.relations.forEach(rel => {
                const hitsClass = rel.hits > 20 ? 'red' : '';

                if(rel.town === null)
                    return;
                    

                tableHTML += `
                    <tr>
                        <td>${rel.title}</td>
                        <td>${rel.town}</td>
                        <td class="${hitsClass}">${rel.hits}</td>
                        <td>${rel.median}</td>
                        <td>${rel.arating.toFixed(1)} ${rel.brating.toFixed(1)}</td>                        
                    </tr>
                `;
            });
            tableHTML += `</tbody></table>`;

            // Create score parameters list
            let scoreHTML = `<div class="score-container"><h3>Score Parameters</h3><ul>`;
            for (const [key, value] of Object.entries(data.score)) {
                scoreHTML += `<li><b>${key}:</b> ${value}</li>`;
            }
            scoreHTML += `</ul></div>`;

            // Insert into div
            resultDiv.innerHTML = tableHTML + scoreHTML;

        
        })
        .catch(error => console.error("Error:", error));
      

    // Здесь будет логика обработки запроса
    resultContainer.innerHTML = `
        <h2>Результаты поиска: ${OID}</h2>
        <p>Информация о компании будет загружена здесь.</p>
        <div id="company-details"></div>
    `;
});


// Обработка кликов по ссылкам компаний
document.querySelectorAll('.company-link').forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        document.getElementById('company-input').value = this.textContent.split(' ')[0];
        document.getElementById('search-form').dispatchEvent(new Event('submit'));
    });
});



function drawRecent(){
    fetch("/recent", {
        method: "GET",
    })
        .then(response => response.json())
        .then(data => {
            const trustedDiv = document.getElementById("trusted2");
            const oidInput = document.getElementById("oid");

            data.trusted.forEach(company => {
                const companyDiv = document.createElement("div");
                companyDiv.classList.add("company");
    
                companyDiv.innerHTML = `
                    <div class="company-title">${company.title}
                    <span class="company-tag trusted-tag">Проверено</span>
                    </div>
                    <div class="company-address">${company.address}</div>
                `;
    
                companyDiv.addEventListener("click", () => {
                    // oidInput.value = company.oid;
                    window.location.href = `/report/${company.oid}`;
                });
    
                trustedDiv.appendChild(companyDiv);
            });
    
        })
        .catch(error => console.error("Error:", error));
}


function make_auto_refresh(){
    // if auto_refresh_btn exists, autorefresh every 10s
    const auto_refresh_btn = document.getElementById("auto_refresh_btn");
    if(auto_refresh_btn){

        setInterval(function(){
            window.location.reload();
        }, 10000);        
    }

}

function main(){
    drawRecent()
    make_auto_refresh()
}

main()