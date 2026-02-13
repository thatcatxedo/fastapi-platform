package config

import (
	"os"
	"path/filepath"

	"github.com/pelletier/go-toml/v2"
)

const (
	ConfigDir  = ".fp"
	ConfigFile = "config.toml"
)

type Platform struct {
	URL      string `toml:"url"`
	Token    string `toml:"token"`
	Username string `toml:"username"`
}

type Config struct {
	Platforms map[string]Platform `toml:"platforms"`
	Active    struct {
		Platform string `toml:"platform"`
	} `toml:"active"`
}

func ConfigPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ConfigDir, ConfigFile)
}

func ConfigDirPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ConfigDir)
}

func Read() (*Config, error) {
	path := ConfigPath()
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return &Config{Platforms: make(map[string]Platform)}, nil
		}
		return nil, err
	}
	var cfg Config
	if err := toml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	if cfg.Platforms == nil {
		cfg.Platforms = make(map[string]Platform)
	}
	return &cfg, nil
}

func Write(cfg *Config) error {
	dir := ConfigDirPath()
	if err := os.MkdirAll(dir, 0700); err != nil {
		return err
	}
	path := ConfigPath()
	data, err := toml.Marshal(cfg)
	if err != nil {
		return err
	}
	if err := os.WriteFile(path, data, 0600); err != nil {
		return err
	}
	return nil
}

func GetActivePlatform() *Platform {
	_, p := GetActivePlatformWithName()
	return p
}

func GetActivePlatformWithName() (string, *Platform) {
	cfg, err := Read()
	if err != nil || cfg == nil {
		return "", nil
	}
	name := cfg.Active.Platform
	if name == "" {
		return "", nil
	}
	p, ok := cfg.Platforms[name]
	if !ok {
		return "", nil
	}
	return name, &p
}

func SavePlatform(name, url, token, username string) error {
	cfg, err := Read()
	if err != nil {
		return err
	}
	cfg.Platforms[name] = Platform{URL: url, Token: token, Username: username}
	cfg.Active.Platform = name
	return Write(cfg)
}

func RemovePlatform(name string) bool {
	cfg, err := Read()
	if err != nil {
		return false
	}
	if _, ok := cfg.Platforms[name]; !ok {
		return false
	}
	delete(cfg.Platforms, name)
	if cfg.Active.Platform == name {
		cfg.Active.Platform = ""
		for n := range cfg.Platforms {
			cfg.Active.Platform = n
			break
		}
	}
	_ = Write(cfg)
	return true
}
