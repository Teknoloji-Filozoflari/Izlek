# Binary bundle recipe: build the payload with scripts/build_rpm.py.
%{!?izlek_version:%global izlek_version 1.0.1}
%global debug_package %{nil}
# Keep the already built Python/Qt bundle intact.
%global __os_install_post %{nil}

Name:           izlek
Version:        %{izlek_version}
Release:        1%{?dist}
Summary:        Local-first film and TV tracking desktop application
License:        GPL-3.0-or-later
URL:            https://github.com/Teknoloji-Filozoflari/Izlek
Source0:        %{name}-%{version}.tar.gz
ExclusiveArch:  x86_64 aarch64
# Scan ELF dependencies; bundled libraries satisfy their own provides.
AutoReqProv:    yes
Requires:       fontconfig

%description
Izlek tracks films, TV shows and episode progress locally using SQLite.
Python and Qt are included in the application bundle.

%prep
%setup -q

%build
# PyInstaller bundle was built and smoke-tested before rpmbuild.

%install
mkdir -p %{buildroot}/usr/lib/izlek %{buildroot}%{_bindir}
cp -a payload/. %{buildroot}/usr/lib/izlek/
printf '#!/bin/sh\nexec /usr/lib/izlek/izlek "$@"\n' > %{buildroot}%{_bindir}/izlek
chmod 0755 %{buildroot}%{_bindir}/izlek
install -Dm644 izlek.desktop %{buildroot}%{_datadir}/applications/izlek.desktop
install -Dm644 izlek.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/izlek.svg

%files
%license LICENSE
/usr/lib/izlek/
%{_bindir}/izlek
%{_datadir}/applications/izlek.desktop
%{_datadir}/icons/hicolor/scalable/apps/izlek.svg
