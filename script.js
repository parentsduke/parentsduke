console.log("JS 已加载");

document.addEventListener("DOMContentLoaded", () => {
  alert("GitHub Pages 中的 JS 生效了！");
});


<script>
const overlay = document.getElementById('overlay');
const overlayImg = document.getElementById('overlay-img');

document.querySelectorAll('.thumb').forEach(img => {
  img.onclick = () => {
    overlay.style.display = 'flex';
    overlayImg.src = img.src;
  };
});

overlay.onclick = () => overlay.style.display = 'none';
</script>
