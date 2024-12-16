{pkgs}: {
  deps = [
    pkgs.openssh
    pkgs.zip
    pkgs.glibcLocales
    pkgs.openssl
    pkgs.postgresql
  ];
}
