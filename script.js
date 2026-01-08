/* ========== 图片单击放大 
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
});   ========== */


/* ========== 视频单击放大（重点） 

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
});   ========== */


/* ================= 图片放大 ================= */

const imgOverlay = document.getElementById('overlay');
const overlayImg = document.getElementById('overlay-img');

document.querySelectorAll('.thumb').forEach(img => {
  img.addEventListener('click', () => {
    overlayImg.src = img.src;
    imgOverlay.style.display = 'flex';
  });
});

// 点黑幕关闭
imgOverlay.addEventListener('click', () => {
  imgOverlay.style.display = 'none';
  overlayImg.src = '';
});

// 阻止点图片本身关闭
overlayImg.addEventListener('click', e => e.stopPropagation());



/* ================= 视频放大 ================= */

const videoOverlay = document.getElementById('video-overlay');
const overlayVideo = document.getElementById('overlay-video');

document.querySelectorAll('.video-wrapper').forEach(wrapper => {
  const video = wrapper.querySelector('.video-box');
  const clickLayer = wrapper.querySelector('.video-click-layer');

  clickLayer.addEventListener('click', () => {
    overlayVideo.src = video.currentSrc || video.src;
    videoOverlay.style.display = 'flex';
    overlayVideo.play();
  });
});

// 点黑幕关闭
videoOverlay.addEventListener('click', () => {
  overlayVideo.pause();
  overlayVideo.src = '';
  videoOverlay.style.display = 'none';
});

// 阻止点视频本身关闭
overlayVideo.addEventListener('click', e => e.stopPropagation());



/* ================= ESC 键统一关闭 ================= */

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {

    // 关闭图片
    imgOverlay.style.display = 'none';
    overlayImg.src = '';

    // 关闭视频
    overlayVideo.pause();
    overlayVideo.src = '';
    videoOverlay.style.display = 'none';
  }
});






