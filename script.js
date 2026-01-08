/* ========== 图片单击放大 ========== */
const thumbs = document.querySelectorAll('.thumb');
const imgOverlay = document.getElementById('overlay');
const overlayImg = document.getElementById('overlay-img');

thumbs.forEach(img => {
  img.addEventListener('click', () => {
    overlayImg.src = img.src;
    imgOverlay.style.display = 'flex';
  });
});

imgOverlay.addEventListener('click', () => {
  imgOverlay.style.display = 'none';
});


/* ========== 视频单击放大（重点） ========== */








const clickLayer = document.querySelector('.video-click-layer');
const video = document.querySelector('.video-box');
const videoOverlay = document.getElementById('video-overlay');
const overlayVideo = document.getElementById('overlay-video');

clickLayer.addEventListener('click', () => {
  overlayVideo.src = video.currentSrc;
  videoOverlay.style.display = 'flex';
  overlayVideo.play();
});

videoOverlay.addEventListener('click', () => {
  overlayVideo.pause();
  overlayVideo.src = '';
  videoOverlay.style.display = 'none';
});
