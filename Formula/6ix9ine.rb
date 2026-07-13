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
  url "file:///Users/rmorales/PycharmProjects/6ix9ine/dist/6ix9ine-v1.0.0.tar.gz"
  sha256 "3bbc09c34d5f028d123d5f3061b7abe8d767295b170ca133702813a75e871421"
  license "MIT"
  version "1.0.0"

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

  def post_install
    ohai "Setting up root privileged helper..."

    # Source files in the Homebrew cellar prefix
    src_bin = bin/"com.rjmorales.6ix9ine.helper"
    src_plist = prefix/"com.rjmorales.6ix9ine.helper.plist"

    # Target system paths
    dst_bin_dir = "/Library/PrivilegedHelperTools"
    dst_bin = "#{dst_bin_dir}/com.rjmorales.6ix9ine.helper"
    dst_plist = "/Library/LaunchDaemons/com.rjmorales.6ix9ine.helper.plist"
    owner_file = "#{dst_bin_dir}/com.rjmorales.6ix9ine.helper.owner"

    begin
      # Create directories if they do not exist
      system "sudo", "mkdir", "-p", dst_bin_dir
      system "sudo", "mkdir", "-p", "/Library/LaunchDaemons"

      # Copy files
      system "sudo", "cp", src_bin.to_s, dst_bin
      system "sudo", "cp", src_plist.to_s, dst_plist

      # Write the owner file with the current user's UID
      uid = Process.uid
      system "sudo", "sh", "-c", "echo #{uid} > #{owner_file}"

      # Set ownership and permissions
      system "sudo", "chown", "root:wheel", dst_bin, dst_plist, owner_file
      system "sudo", "chmod", "755", dst_bin
      system "sudo", "chmod", "644", dst_plist

      # Register/Load daemon with launchctl
      ohai "Registering and starting LaunchDaemon..."
      # Force bootout first if it was already bootstrapped
      begin
        system "sudo", "launchctl", "bootout", "system", dst_plist
      rescue => e
        # Ignore bootout errors
      end
      system "sudo", "launchctl", "bootstrap", "system", dst_plist
    rescue => e
      opoo "Could not automatically register root helper daemon: #{e.message}"
      opoo "Please run '6ix9ine setup-privileged-helper' manually to complete setup."
    end
  end

  def uninstall
    ohai "Stopping and unregistering LaunchDaemon..."
    dst_plist = "/Library/LaunchDaemons/com.rjmorales.6ix9ine.helper.plist"
    dst_bin = "/Library/PrivilegedHelperTools/com.rjmorales.6ix9ine.helper"
    owner_file = "/Library/PrivilegedHelperTools/com.rjmorales.6ix9ine.helper.owner"

    begin
      # Stop and bootout daemon
      system "sudo", "launchctl", "bootout", "system", dst_plist if File.exist?(dst_plist)
      # Clean up files
      system "sudo", "rm", "-f", dst_plist, dst_bin, owner_file
      # Reset sleep setting to default
      system "sudo", "pmset", "disablesleep", "0"
    rescue => e
      opoo "Could not automatically unregister helper daemon: #{e.message}"
    end
  end

  def caveats
    <<~EOS
      6ix9ine has been installed successfully.
      The root privileged helper daemon has been loaded and registered with launchctl.

      To start the user-level background daemon, run:
        6ix9ine daemon-start

      To open the interactive dashboard, run:
        t69
    EOS
  end
end
