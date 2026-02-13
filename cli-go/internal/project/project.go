package project

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

const (
	ProjectFile = ".fp.yaml"
)

var AllowedExtensions = map[string]bool{
	".py": true, ".css": true, ".js": true, ".svg": true,
	".html": true, ".json": true, ".txt": true,
}

var SkipDirs = map[string]bool{
	"__pycache__": true, ".venv": true, "node_modules": true,
}

type Project struct {
	Name       string            `yaml:"name"`
	Entrypoint string            `yaml:"entrypoint"`
	Env        map[string]string `yaml:"env"`
	Database   interface{}       `yaml:"database"`
}

func FindProjectFile(start string) (string, bool) {
	if start == "" {
		start, _ = os.Getwd()
	}
	dir := start
	for {
		candidate := filepath.Join(dir, ProjectFile)
		if _, err := os.Stat(candidate); err == nil {
			return candidate, true
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "", false
}

func Read(path string) (*Project, error) {
	if path == "" {
		return nil, fmt.Errorf("no %s found. Run 'fp init' first", ProjectFile)
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var p Project
	if err := yaml.Unmarshal(data, &p); err != nil {
		return nil, err
	}
	if p.Entrypoint == "" {
		p.Entrypoint = "app.py"
	}
	return &p, nil
}

func ReadFromCwd() (*Project, string, error) {
	fp, ok := FindProjectFile("")
	if !ok {
		return nil, "", fmt.Errorf("no %s found. Run 'fp init' first", ProjectFile)
	}
	p, err := Read(fp)
	if err != nil {
		return nil, "", err
	}
	dir := filepath.Dir(fp)
	return p, dir, nil
}

func Write(dir string, p *Project) error {
	data, err := yaml.Marshal(p)
	if err != nil {
		return err
	}
	path := filepath.Join(dir, ProjectFile)
	return os.WriteFile(path, data, 0644)
}

func shouldSkip(rel string) bool {
	parts := strings.Split(filepath.ToSlash(rel), "/")
	for _, p := range parts {
		if strings.HasPrefix(p, ".") || SkipDirs[p] {
			return true
		}
	}
	return false
}

func CollectFiles(dir, entrypoint string) (map[string]string, error) {
	files := make(map[string]string)
	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}
		rel, err := filepath.Rel(dir, path)
		if err != nil {
			return err
		}
		rel = filepath.ToSlash(rel)
		ext := strings.ToLower(filepath.Ext(path))
		if !AllowedExtensions[ext] {
			return nil
		}
		if shouldSkip(rel) {
			return nil
		}
		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		files[rel] = string(content)
		return nil
	})
	if err != nil {
		return nil, err
	}
	if _, ok := files[entrypoint]; !ok {
		return nil, fmt.Errorf("entrypoint '%s' not found in %s", entrypoint, dir)
	}
	return files, nil
}

func DetectMode(files map[string]string) string {
	pyCount := 0
	hasNonPy := false
	for f := range files {
		if strings.HasSuffix(f, ".py") {
			pyCount++
		} else {
			hasNonPy = true
		}
	}
	if pyCount > 1 || hasNonPy {
		return "multi"
	}
	return "single"
}
