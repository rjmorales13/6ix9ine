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
  version "1.0.2"
  license "MIT"

  on_arm do
    url "https://github.com/rjmorales13/6ix9ine/releases/download/v1.0.2/6ix9ine-v1.0.2-arm64.tar.gz"
    sha256 "e626ece96f4eae75b53f0ee04ff5acdcc74cdce5cf3a3239e91b9e546dcf65bd"
  end

  on_intel do
    url "https://github.com/rjmorales13/6ix9ine/releases/download/v1.0.2/6ix9ine-v1.0.2-x86_64.tar.gz"
    sha256 "fbf3546bad5934fcbc1ef4910bed5b12baff1292be2376155e347659a666e830"
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
