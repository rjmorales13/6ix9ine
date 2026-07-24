# Redefine Formulary.class_s to support digit-prefixed class naming in Homebrew
module ::Formulary
  class << self
    unless method_defined?(:old_class_s)
      alias_method :old_class_s, :class_s
      def class_s(name)
        if name == "6ix9ine"
          "SixixNineine"
        else
          old_class_s(name)
        end
      end
    end
  end
end

class SixixNineine < Formula
  desc "Keep your Mac awake only while AI agents are working"
  homepage "https://github.com/rjmorales13/6ix9ine"
  version "1.0.5"
  license "MIT"

  on_arm do
    url "https://github.com/rjmorales13/6ix9ine/releases/download/v1.0.5/6ix9ine-v1.0.5-arm64.tar.gz"
    sha256 "f9f6579c0eb6eddfdbcf4ff53fb3103bd9366abf6c93ad5d505edfe6de768ac1"
  end

  on_intel do
    url "https://github.com/rjmorales13/6ix9ine/releases/download/v1.0.5/6ix9ine-v1.0.5-x86_64.tar.gz"
    sha256 "44bd8e02c8178b8cc8114978f8bb66a4a0e05b08f030a84f11766adab80053ec"
  end

  def install
    # Detect macOS version
    if MacOS.version < :sonoma
      odie "6ix9ine requires macOS Sonoma (14.0) or newer!"
    end

    # Install binaries
    bin.install "6ix9ine"
    bin.install "t69"
    bin.install "com.rjmorales.6ix9ine.daemon"
    bin.install "com.rjmorales.6ix9ine.helper"

    # Install helper plist to prefix
    prefix.install "com.rjmorales.6ix9ine.helper.plist"

    # Install man pages
    man1.install "man/6ix9ine.1"
    man1.install "man/t69.1"
  end

  def caveats
    <<~EOS
      6ix9ine has been installed successfully.

      To complete setup, you must configure the root privileged helper:
        6ix9ine setup-privileged-helper

      To start the user-level background daemon, run:
        6ix9ine daemon-start

      To open the interactive dashboard, run:
        t69
    EOS
  end

  test do
    assert_match "6ix9ine v#{version}", shell_output("#{bin}/6ix9ine --version")
    assert_match "usage: t69", shell_output("#{bin}/t69 --help")
  end
end
