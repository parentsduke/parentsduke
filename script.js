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

document.querySelectorAll('.video-wrapper').forEach(wrapper => {
  const video = wrapper.querySelector('.video-box');
  const clickLayer = wrapper.querySelector('.video-click-layer');

  clickLayer.addEventListener('click', () => {
    const overlay = document.getElementById('video-overlay');
    const overlayVideo = document.getElementById('overlay-video');

    overlayVideo.src = video.currentSrc || video.src;
    overlay.style.display = 'flex';
    overlayVideo.play();
  });
});

// 点击遮罩关闭
document.getElementById('video-overlay').addEventListener('click', () => {
  const overlayVideo = document.getElementById('overlay-video');
  overlayVideo.pause();
  overlayVideo.src = '';
  document.getElementById('video-overlay').style.display = 'none';
});







