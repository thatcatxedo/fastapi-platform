package cmd

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/api"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/config"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/project"
)

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Scaffold a new project in the current directory",
	RunE:  runInit,
}

var (
	initTemplate string
	initName     string
)

func init() {
	initCmd.Flags().StringVarP(&initTemplate, "template", "t", "", "Create from a platform template")
	initCmd.Flags().StringVarP(&initName, "name", "n", "", "App name (default: directory name)")
}

const fastAPIStarter = `from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Hello from FastAPI Platform!"}
`

const fastHTMLStarter = `from fasthtml.common import *

app, rt = fast_app()


@rt("/")
def home():
    return H1("Hello from FastAPI Platform!")
`

func runInit(cmd *cobra.Command, args []string) error {
	cwd, _ := os.Getwd()
	if _, err := os.Stat(filepath.Join(cwd, project.ProjectFile)); err == nil {
		fmt.Fprintf(os.Stderr, "%s already exists in this directory.\n", project.ProjectFile)
		os.Exit(1)
	}

	appName := initName
	if appName == "" {
		appName = filepath.Base(cwd)
	}

	if initTemplate != "" {
		return initFromTemplate(appName)
	}

	reader := bufio.NewReader(os.Stdin)
	fmt.Print("Framework [fastapi/fasthtml] (fastapi): ")
	framework, _ := reader.ReadString('\n')
	framework = strings.TrimSpace(strings.ToLower(framework))
	if framework == "" {
		framework = "fastapi"
	}
	if framework != "fasthtml" {
		framework = "fastapi"
	}

	var code string
	if framework == "fastapi" {
		code = fastAPIStarter
	} else {
		code = fastHTMLStarter
	}

	if err := os.WriteFile(filepath.Join(cwd, "app.py"), []byte(code), 0644); err != nil {
		return err
	}
	if err := project.Write(cwd, &project.Project{Name: appName, Entrypoint: "app.py"}); err != nil {
		return err
	}

	fmt.Printf("Created app.py + %s\n", project.ProjectFile)
	fmt.Printf("  App name: %s\n", appName)
	fmt.Printf("  Framework: %s\n", framework)
	fmt.Println()
	fmt.Println("Next steps:")
	fmt.Println("  fp dev     — run locally with hot reload")
	fmt.Println("  fp deploy  — deploy to the platform")
	return nil
}

func initFromTemplate(appName string) error {
	p := config.GetActivePlatform()
	if p == nil {
		fmt.Fprintln(os.Stderr, "Not authenticated. Run 'fp auth login <url>' to use templates from the platform.")
		os.Exit(1)
	}

	client := api.NewClient(p.URL, p.Token)
	templates, err := client.ListTemplates()
	if err != nil {
		var pe *api.PlatformError
		if errors.As(err, &pe) {
			fmt.Fprintf(os.Stderr, "Failed to fetch templates: %s\n", pe.Message)
			os.Exit(1)
		}
		return err
	}

	templateName := strings.ToLower(initTemplate)
	var match map[string]interface{}
	for _, t := range templates {
		if n, _ := t["name"].(string); strings.ToLower(n) == templateName {
			match = t
			break
		}
	}
	if match == nil {
		fmt.Fprintf(os.Stderr, "Template '%s' not found.\n", initTemplate)
		fmt.Println("Available templates:")
		for _, t := range templates {
			if n, _ := t["name"].(string); n != "" {
				fmt.Printf("  - %s\n", n)
			}
		}
		os.Exit(1)
	}

	cwd, _ := os.Getwd()
	entrypoint := "app.py"
	if e, ok := match["entrypoint"].(string); ok && e != "" {
		entrypoint = e
	}

	if mode, _ := match["mode"].(string); mode == "multi" {
		files, _ := match["files"].(map[string]interface{})
		if files != nil {
			for filename, content := range files {
				if s, ok := content.(string); ok {
					fpath := filepath.Join(cwd, filename)
					if err := os.MkdirAll(filepath.Dir(fpath), 0755); err != nil {
						return err
					}
					if err := os.WriteFile(fpath, []byte(s), 0644); err != nil {
						return err
					}
				}
			}
			tname, _ := match["name"].(string)
			fmt.Printf("Created %d files from template %s\n", len(files), tname)
		}
	} else if code, ok := match["code"].(string); ok {
		if err := os.WriteFile(filepath.Join(cwd, "app.py"), []byte(code), 0644); err != nil {
			return err
		}
		tname, _ := match["name"].(string)
		fmt.Printf("Created app.py from template %s\n", tname)
	} else {
		fmt.Fprintln(os.Stderr, "Template has no code or files.")
		os.Exit(1)
	}

	if err := project.Write(cwd, &project.Project{Name: appName, Entrypoint: entrypoint}); err != nil {
		return err
	}
	fmt.Printf("  App name: %s\n", appName)
	fmt.Println()
	fmt.Println("Next steps:")
	fmt.Println("  fp dev     — run locally with hot reload")
	fmt.Println("  fp deploy  — deploy to the platform")
	return nil
}
