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
