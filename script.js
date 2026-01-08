
const thumbs = document.querySelectorAll('.thumb');
const overlay = document.getElementById('overlay');
const overlayImg = document.getElementById('overlay-img');

thumbs.forEach(img => {
  img.addEventListener('click', () => {
    overlayImg.src = img.src;
    overlay.style.display = 'flex';
  });
});

overlay.addEventListener('click', () => {
  overlay.style.display = 'none';
});
