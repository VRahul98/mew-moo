// Play pet sounds on image hover

document.addEventListener("DOMContentLoaded", function () {
    const images = document.querySelectorAll("img");

    images.forEach((img) => {
        img.addEventListener("mouseover", () => {
            const audio = new Audio(`/static/sounds/${img.alt || "default"}.mp3`);
            audio.play();
        });
    });
});
document.addEventListener("DOMContentLoaded", function () {
    const splash = document.getElementById("splash-screen");
    setTimeout(() => {
        splash.style.display = "none";
    }, 4000);
});
