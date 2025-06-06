{pkgs}: {
  deps = [
    pkgs.tesseract
    pkgs.libGLU
    pkgs.libGL
    pkgs.geckodriver
    pkgs.glibcLocales
    pkgs.chromium
    pkgs.chromedriver
    pkgs.google-chrome
  ];
}
