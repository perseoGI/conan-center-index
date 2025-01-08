from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy, get, rm, rmdir
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version
from conan.errors import ConanInvalidConfiguration
import os

required_conan_version = ">=2.0.9"


class OpenImageIOConan(ConanFile):
    name = "openimageio"
    description = (
        "OpenImageIO is a library for reading and writing images, and a bunch "
        "of related classes, utilities, and applications. There is a "
        "particular emphasis on formats and functionality used in "
        "professional, large-scale animation and visual effects work for film."
    )
    topics = ("vfx", "image", "picture")
    license = "Apache-2.0", "BSD-3-Clause"
    homepage = "http://www.openimageio.org/"
    url = "https://github.com/conan-io/conan-center-index"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_libjpeg": ["libjpeg", "libjpeg-turbo"],
        "with_libpng": [True, False],
        "with_freetype": [True, False],
        "with_hdf5": [True, False],
        "with_opencolorio": [True, False],
        "with_opencv": [True, False],
        "with_tbb": [True, False],
        "with_dicom": [True, False],
        "with_ffmpeg": [True, False],
        "with_giflib": [True, False],
        "with_libheif": [True, False],
        "with_raw": [True, False],
        "with_openjpeg": [True, False],
        "with_openvdb": [True, False],
        "with_ptex": [True, False],
        "with_libwebp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_libjpeg": "libjpeg",
        "with_libpng": True,
        "with_freetype": True,
        "with_hdf5": True,
        "with_opencolorio": True,
        "with_opencv": False,
        "with_tbb": False,
        "with_dicom": False,  # Heavy dependency, disabled by default
        "with_ffmpeg": True,
        "with_giflib": True,
        "with_libheif": True,
        "with_raw": False,  # libraw is available under CDDL-1.0 or LGPL-2.1, for this reason it is disabled by default
        "with_openjpeg": True,
        "with_openvdb": True,
        "with_ptex": True,
        "with_libwebp": True,
    }
    implements = ["auto_shared_fpic"]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Required libraries
        self.requires("zlib/[>=1.2.11 <2]")
        self.requires("boost/1.84.0")
        self.requires("libtiff/4.6.0")
        self.requires("imath/3.1.9", transitive_headers=True)
        self.requires("openexr/3.2.3")
        if self.options.with_libjpeg == "libjpeg":
            self.requires("libjpeg/9e")
        elif self.options.with_libjpeg == "libjpeg-turbo":
            self.requires("libjpeg-turbo/3.0.2")
        self.requires("pugixml/1.14")
        self.requires("libsquish/1.15")
        self.requires("tsl-robin-map/1.2.1")
        if Version(self.version) >= "2.4.17.0":
            self.requires("fmt/10.2.1", transitive_headers=True)
        else:
            self.requires("fmt/9.1.0", transitive_headers=True)

        # Optional libraries
        if self.options.with_libpng:
            self.requires("libpng/[>=1.6 <2]")
        if self.options.with_freetype:
            self.requires("freetype/2.13.2")
        if self.options.with_hdf5:
            self.requires("hdf5/1.14.3")
        if self.options.with_opencolorio:
            self.requires("opencolorio/2.3.1")
        if self.options.with_opencv:
            self.requires("opencv/4.8.1")
        if self.options.with_tbb:
            self.requires("onetbb/2021.10.0")
        if self.options.with_dicom:
            self.requires("dcmtk/3.6.7")
        if self.options.with_ffmpeg:
            self.requires("ffmpeg/6.1")
        # TODO: Field3D dependency
        if self.options.with_giflib:
            self.requires("giflib/5.2.1")
        if self.options.with_libheif:
            self.requires("libheif/1.16.2")
        if self.options.with_raw:
            self.requires("libraw/0.21.3")
        if self.options.with_openjpeg:
            self.requires("openjpeg/2.5.2")
        if self.options.with_openvdb:
            self.requires("openvdb/11.0.0")
        if self.options.with_ptex:
            self.requires("ptex/2.4.2")
        if self.options.with_libwebp:
            self.requires("libwebp/1.3.2")
        # TODO: R3DSDK dependency
        # TODO: Nuke dependency

    def validate(self):
        check_min_cppstd(self, 14)
        if is_msvc(self) and is_msvc_static_runtime(self) and self.options.shared:
            raise ConanInvalidConfiguration(
                "Building shared library with static runtime is not supported!"
            )
        if self.options.with_raw and not self.dependencies["libraw"].options.get_safe("build_thread_safe", False):
            raise ConanInvalidConfiguration(f"{self.ref} with libraw requires libraw/*:build_thread_safe=True")

        if self.options.with_opencv and self.options.with_ffmpeg != self.dependencies["opencv"].options.get_safe("with_ffmpeg", True):
            raise ConanInvalidConfiguration(f"{self.ref} with opencv requires with_ffmpeg to be the same as opencv")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # CMake options
        tc.variables["CMAKE_DEBUG_POSTFIX"] = ""  # Needed for 2.3.x.x+ versions
        tc.variables["OIIO_BUILD_TOOLS"] = True
        tc.variables["OIIO_BUILD_TESTS"] = False
        tc.variables["BUILD_DOCS"] = False
        tc.variables["INSTALL_DOCS"] = False
        tc.variables["INSTALL_FONTS"] = False
        tc.variables["INSTALL_CMAKE_HELPER"] = False
        tc.variables["EMBEDPLUGINS"] = True
        tc.variables["USE_PYTHON"] = False
        tc.variables["USE_EXTERNAL_PUGIXML"] = True
        tc.variables["BUILD_MISSING_FMT"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.variables["USE_R3DSDK"] = False
        tc.variables["USE_NUKE"] = False
        tc.variables["USE_OPENGL"] = False
        tc.variables["USE_QT"] = False
        tc.variables["INTERNALIZE_FMT"] = False
        tc.cache_variables["CMAKE_REQUIRE_FIND_PACKAGE_fmt"] = True
        tc.cache_variables["ROBINMAP_FOUND"] = True
        tc.cache_variables["LIBRAW_FOUND"] = self.options.with_raw

        options_target_map = {"with_libpng": "PNG", "with_freetype": "Freetype", "with_opencolorio": "OpenColorIO", "with_opencv": "OpenCV",
            "with_tbb": "TBB", "with_dicom": "DCMTK", "with_ffmpeg": "FFmpeg", "with_giflib": "GIF", "with_libheif": "Libheif",
            "with_raw": "LibRaw", "with_openjpeg": "OpenJPEG", "with_openvdb": "OpenVDB", "with_ptex": "Ptex", "with_libwebp": "WebP"}
        for option, cmake_var in options_target_map.items():
            if getattr(self.options, option):
                if cmake_var not in ["OpenJPEG", "WebP", "FFmpeg"]: # Already required by transitives
                    tc.cache_variables[f"CMAKE_REQUIRE_FIND_PACKAGE_{cmake_var}"] = True
            else:
                tc.cache_variables[f"CMAKE_DISABLE_FIND_PACKAGE_{cmake_var}"] = True

        if self.options.with_libjpeg == "libjpeg":
            tc.cache_variables[f"CMAKE_DISABLE_FIND_PACKAGE_libjpeg-turbo"] = True
        else:
            tc.cache_variables[f"CMAKE_REQUIRE_FIND_PACKAGE_libjpeg-turbo"] = True

        tc.generate()
        deps = CMakeDeps(self)
        deps.set_property("ffmpeg", "cmake_file_name", "FFmpeg")  # ffmpeg -> FFmpeg
        deps.set_property("ffmpeg", "cmake_additional_variables_prefixes", ["FFMPEG"])
        # TODO do not disable libheif on macos
        deps.set_property("libheif", "cmake_file_name", "Libheif")  # libheif -> Libheif
        deps.set_property("libheif", "cmake_additional_variables_prefixes", ["LIBHEIF"])
        deps.set_property("libraw", "cmake_file_name", "LibRaw")    # libraw -> LibRaw
        deps.set_property("libraw", "cmake_additional_variables_prefixes", ["LibRaw_r"])

        deps.set_property("dcmtk", "cmake_target_name", "DCMTK::DCMTK")    # Create a global target for DCMTK
        deps.set_property("ptex", "cmake_file_name", "Ptex")  # ptex -> Ptex

        deps.set_property("tsl-robin-map", "cmake_file_name", "Robinmap")
        deps.set_property("tsl-robin-map", "cmake_additional_variables_prefixes", ["ROBINMAP"])
        deps.set_property("fmt", "cmake_additional_variables_prefixes", ["FMT"])
        deps.set_property("fmt", "cmake_target_name", "fmt::fmt-header-only")
        deps.set_property("openvdb", "cmake_additional_variables_prefixes", ["OPENVDB"])

        if self.options.with_libjpeg == "libjpeg-turbo":
            deps.set_property("libjpeg-turbo", "cmake_target_aliases", ["JPEG::JPEG"])

        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE*.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share"))
        if self.settings.os == "Windows":
            for vc_file in ("concrt", "msvcp", "vcruntime"):
                rm(self, f"{vc_file}*.dll", os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    @staticmethod
    def _conan_comp(name):
        return f"openimageio_{name.lower()}"

    def _add_component(self, name):
        component = self.cpp_info.components[self._conan_comp(name)]
        component.set_property("cmake_target_name", f"OpenImageIO::{name}")
        component.names["cmake_find_package"] = name
        component.names["cmake_find_package_multi"] = name
        return component

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenImageIO")
        self.cpp_info.set_property("pkg_config_name", "OpenImageIO")

        # OpenImageIO::OpenImageIO_Util
        open_image_io_util = self._add_component("OpenImageIO_Util")
        open_image_io_util.libs = ["OpenImageIO_Util"]
        open_image_io_util.requires = [
            "boost::filesystem",
            "boost::thread",
            "boost::system",
            "boost::regex",
            "imath::imath",
            "openexr::openexr",
        ]
        if self.settings.os in ["Linux", "FreeBSD"]:
            open_image_io_util.system_libs.extend(
                ["dl", "m", "pthread"]
            )
        if self.options.with_tbb:
            open_image_io_util.requires.append("onetbb::onetbb")

        # OpenImageIO::OpenImageIO
        open_image_io = self._add_component("OpenImageIO")
        open_image_io.libs = ["OpenImageIO"]
        open_image_io.requires = [
            "openimageio_openimageio_util",
            "zlib::zlib",
            "boost::thread",
            "boost::system",
            "boost::container",
            "boost::regex",
            "libtiff::libtiff",
            "pugixml::pugixml",
            "tsl-robin-map::tsl-robin-map",
            "libsquish::libsquish",
            "fmt::fmt",
            "imath::imath",
            "openexr::openexr",
        ]

        if self.options.with_libjpeg == "libjpeg":
            open_image_io.requires.append("libjpeg::libjpeg")
        elif self.options.with_libjpeg == "libjpeg-turbo":
            open_image_io.requires.append(
                "libjpeg-turbo::libjpeg-turbo"
            )
        if self.options.with_libpng:
            open_image_io.requires.append("libpng::libpng")
        if self.options.with_freetype:
            open_image_io.requires.append("freetype::freetype")
        if self.options.with_hdf5:
            open_image_io.requires.append("hdf5::hdf5")
        if self.options.with_opencolorio:
            open_image_io.requires.append("opencolorio::opencolorio")
        if self.options.with_opencv:
            open_image_io.requires.append("opencv::opencv")
        if self.options.with_dicom:
            open_image_io.requires.append("dcmtk::dcmtk")
        if self.options.with_ffmpeg:
            open_image_io.requires.append("ffmpeg::ffmpeg")
        if self.options.with_giflib:
            open_image_io.requires.append("giflib::giflib")
        if self.options.with_libheif:
            open_image_io.requires.append("libheif::libheif")
        if self.options.with_raw:
            open_image_io.requires.append("libraw::libraw")
        if self.options.with_openjpeg:
            open_image_io.requires.append("openjpeg::openjpeg")
        if self.options.with_openvdb:
            open_image_io.requires.append("openvdb::openvdb")
        if self.options.with_ptex:
            open_image_io.requires.append("ptex::ptex")
        if self.options.with_libwebp:
            open_image_io.requires.append("libwebp::libwebp")
        if self.settings.os in ["Linux", "FreeBSD"]:
            open_image_io.system_libs.extend(["dl", "m", "pthread"])

        if not self.options.shared:
            open_image_io.defines.append("OIIO_STATIC_DEFINE")
