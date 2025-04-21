
function make_auto_refresh(){
    // if auto_refresh_btn exists, autorefresh every 10s
    const auto_refresh_btn = document.getElementById("auto_refresh_btn");
    if(auto_refresh_btn){
        let secondsLeft = 10;
        console.log(secondsLeft);

        const countdownInterval = setInterval(function() {
            secondsLeft--;
            console.log(secondsLeft);
            auto_refresh_btn.textContent = `Обновить (${secondsLeft})`;
            
            if (secondsLeft <= 0) {
                clearInterval(countdownInterval); // Останавливаем отсчет
                window.location.reload();
            }
        }, 1000); // Обновляем каждую секунду
    

    }

}

function turnstileCallback(){
    const submit_btn = document.getElementById('submit_btn');
    submit_btn.disabled = false;
}

function make_toggle_link(){
    document.getElementById("toggle-link")?.addEventListener("click", function(e) {
        e.preventDefault();
        document.getElementById("recalc-box").classList.toggle("show");
    });
   
}

function main(){
    make_auto_refresh();
    make_toggle_link();
}

function setQuery(text) {
    document.getElementById('oid').value = text;
}

main()