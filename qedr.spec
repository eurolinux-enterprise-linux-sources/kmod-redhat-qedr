%define kmod_name		qedr
%define kmod_vendor		redhat
%define kmod_driver_version	8.10.10.0_dup7.4
%define kmod_rpm_release	2
%define kmod_kernel_version	3.10.0-693.el7
%define kmod_kbuild_dir		drivers/infiniband/hw/qedr
%define kmod_dependencies       %{nil}
%define kmod_build_dependencies	%{nil}
%define kmod_devel_package	0

%{!?dist: %define dist .el7_4}

Source0:	%{kmod_name}-%{kmod_vendor}-%{kmod_driver_version}.tar.bz2
# Source code patches
Patch0:	0000-version-bump.patch

%define findpat %( echo "%""P" )
%define __find_requires /usr/lib/rpm/redhat/find-requires.ksyms
%define __find_provides /usr/lib/rpm/redhat/find-provides.ksyms %{kmod_name} %{?epoch:%{epoch}:}%{version}-%{release}
%define sbindir %( if [ -d "/sbin" -a \! -h "/sbin" ]; then echo "/sbin"; else echo %{_sbindir}; fi )
%define dup_state_dir %{_localstatedir}/lib/rpm-state/kmod-dups
%define kver_state_dir %{dup_state_dir}/kver
%define kver_state_file %{kver_state_dir}/%{kmod_kernel_version}.%(arch)
%define dup_module_list %{dup_state_dir}/rpm-kmod-%{kmod_name}-modules

Name:		kmod-redhat-qedr
Version:	%{kmod_driver_version}
Release:	%{kmod_rpm_release}%{?dist}
Summary:	qedr module for Driver Update Program
Group:		System/Kernel
License:	GPLv2
URL:		http://www.kernel.org/
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires:	kernel-devel = %kmod_kernel_version redhat-rpm-config kernel-abi-whitelists
ExclusiveArch:	x86_64
%global kernel_source() /usr/src/kernels/%{kmod_kernel_version}.$(arch)

%global _use_internal_dependency_generator 0
Provides:	kernel-modules = %kmod_kernel_version.%{_target_cpu}
Provides:	kmod-%{kmod_name} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires(post):	%{sbindir}/weak-modules
Requires(postun):	%{sbindir}/weak-modules
Requires:	kernel >= 3.10.0-693.el7
Requires:	kernel < 3.10.0-694.el7
%if 0
Requires: firmware(%{kmod_name}) = ENTER_FIRMWARE_VERSION
%endif
%if "%{kmod_build_dependencies}" != ""
BuildRequires:  %{kmod_build_dependencies}
%endif
%if "%{kmod_dependencies}" != ""
Requires:       %{kmod_dependencies}
%endif
# if there are multiple kmods for the same driver from different vendors,
# they should conflict with each other.
Conflicts:	kmod-%{kmod_name}

%description
qedr module for Driver Update Program

%if 0

%package -n kmod-redhat-qedr-firmware
Version:	ENTER_FIRMWARE_VERSION
Summary:	qedr firmware for Driver Update Program
Provides:	firmware(%{kmod_name}) = ENTER_FIRMWARE_VERSION
Provides:	kernel-modules = %{kmod_kernel_version}.%{_target_cpu}
%description -n  kmod-redhat-qedr-firmware
qedr firmware for Driver Update Program


%files -n kmod-redhat-qedr-firmware
%defattr(644,root,root,755)
%{FIRMWARE_FILES}

%endif

# Development package
%if 0%{kmod_devel_package}
%package -n kmod-redhat-qedr-devel
Version:	%{kmod_driver_version}
Requires:	kernel >= 3.10.0-693.el7
Requires:	kernel < 3.10.0-694.el7
Summary:	qedr development files for Driver Update Program

%description -n  kmod-redhat-qedr-devel
qedr development files for Driver Update Program


%files -n kmod-redhat-qedr-devel
%defattr(644,root,root,755)
/usr/share/kmod-%{kmod_vendor}-%{kmod_name}/Module.symvers
%endif

%post
modules=( $(find /lib/modules/%{kmod_kernel_version}.%(arch)/extra/kmod-%{kmod_vendor}-%{kmod_name} | grep '\.ko$') )
printf '%s\n' "${modules[@]}" | %{sbindir}/weak-modules --add-modules --no-initramfs

mkdir -p "%{kver_state_dir}"
touch "%{kver_state_file}"

exit 0

%posttrans
# We have to re-implement part of weak-modules here because it doesn't allow
# calling initramfs regeneration separately
if [ -f "%{kver_state_file}" ]; then
	k="%{kmod_kernel_version}.%(arch)"
	tmp_initramfs="/boot/initramfs-$k.tmp"
	dst_initramfs="/boot/initramfs-$k.img"

	# The same check as in weak-modules: we assume that the kernel present
	# if the symvers file exists.
	if [ -e "/boot/symvers-$k.gz" ]; then
		/usr/bin/dracut -f "$tmp_initramfs" "$k" || exit 1
		cmp -s "$tmp_initramfs" "$dst_initramfs"
		if [ "$?" = 1 ]; then
			mv "$tmp_initramfs" "$dst_initramfs"
		else
			rm -f "$tmp_initramfs"
		fi
	fi

	rm -f "%{kver_state_file}"
	rmdir "%{kver_state_dir}" 2> /dev/null
fi

rmdir "%{dup_state_dir}" 2> /dev/null

exit 0

%preun
if rpm -q --filetriggers kmod 2> /dev/null| grep -q "Trigger for weak-modules call on kmod removal"; then
	mkdir -p "%{kver_state_dir}"
	touch "%{kver_state_file}"
fi

mkdir -p "%{dup_state_dir}"
rpm -ql kmod-redhat-qedr-%{kmod_driver_version}-%{kmod_rpm_release}%{?dist}.$(arch) | \
	grep '\.ko$' > "%{dup_module_list}"

%postun
if rpm -q --filetriggers kmod 2> /dev/null| grep -q "Trigger for weak-modules call on kmod removal"; then
	initramfs_opt="--no-initramfs"
else
	initramfs_opt=""
fi

modules=( $(cat "%{dup_module_list}") )
rm -f "%{dup_module_list}"
printf '%s\n' "${modules[@]}" | %{sbindir}/weak-modules --remove-modules $initramfs_opt

rmdir "%{dup_state_dir}" 2> /dev/null

exit 0

%files
%defattr(644,root,root,755)
/lib/modules/%{kmod_kernel_version}.%(arch)
/etc/depmod.d/%{kmod_name}.conf
/usr/share/doc/kmod-%{kmod_name}/greylist.txt

%prep
%setup -n %{kmod_name}-%{kmod_vendor}-%{kmod_driver_version}

%patch0 -p1
set -- *
mkdir source
mv "$@" source/
mkdir obj

%build
rm -rf obj
cp -r source obj
make %{_smp_mflags} -C %{kernel_source} M=$PWD/obj/%{kmod_kbuild_dir} \
	NOSTDINC_FLAGS="-I $PWD/obj/include -I $PWD/obj/include/uapi" \
	%{nil}
# mark modules executable so that strip-to-file can strip them
find obj/%{kmod_kbuild_dir} -name "*.ko" -type f -exec chmod u+x '{}' +

whitelist="/lib/modules/kabi-current/kabi_whitelist_%{_target_cpu}"
for modules in $( find obj/%{kmod_kbuild_dir} -name "*.ko" -type f -printf "%{findpat}\n" | sed 's|\.ko$||' | sort -u ) ; do
	# update depmod.conf
	module_weak_path=$(echo $modules | sed 's/[\/]*[^\/]*$//')
	if [ -z "$module_weak_path" ]; then
		module_weak_path=%{name}
	else
		module_weak_path=%{name}/$module_weak_path
	fi
	echo "override $(echo $modules | sed 's/.*\///') $(echo %{kmod_kernel_version} | sed 's/\.[^\.]*$//').* weak-updates/$module_weak_path" >> source/depmod.conf

	# update greylist
	nm -u obj/%{kmod_kbuild_dir}/$modules.ko | sed 's/.*U //' |  sed 's/^\.//' | sort -u | while read -r symbol; do
		grep -q "^\s*$symbol\$" $whitelist || echo "$symbol" >> source/greylist
	done
done
sort -u source/greylist | uniq > source/greylist.txt

%install
export INSTALL_MOD_PATH=$RPM_BUILD_ROOT
export INSTALL_MOD_DIR=extra/%{name}
make -C %{kernel_source} modules_install \
	M=$PWD/obj/%{kmod_kbuild_dir}
# Cleanup unnecessary kernel-generated module dependency files.
find $INSTALL_MOD_PATH/lib/modules -iname 'modules.*' -exec rm {} \;

install -m 644 -D source/depmod.conf $RPM_BUILD_ROOT/etc/depmod.d/%{kmod_name}.conf
install -m 644 -D source/greylist.txt $RPM_BUILD_ROOT/usr/share/doc/kmod-%{kmod_name}/greylist.txt
%if 0
%{FIRMWARE_FILES_INSTALL}
%endif
%if 0%{kmod_devel_package}
install -m 644 -D $PWD/obj/%{kmod_kbuild_dir}/Module.symvers $RPM_BUILD_ROOT/usr/share/kmod-%{kmod_vendor}-%{kmod_name}/Module.symvers
%endif

%clean
rm -rf $RPM_BUILD_ROOT

%changelog
* Tue Dec 19 2017 Eugene Syromiatnikov <esyr@redhat.com> 8.10.10.0_dup7.4-2
- Do not call dracut on non-existing kernel

* Thu Dec 14 2017 Eugene Syromiatnikov <esyr@redhat.com> 8.10.10.0_dup7.4-1
- 0413ea41707374d85a707b850cd0b318d3d5d132
- Resolves: #bz1525991, #bz1525992
- qedr module for Driver Update Program
