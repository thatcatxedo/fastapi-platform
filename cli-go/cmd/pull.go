package cmd

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/api"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/project"
)

var pullCmd = &cobra.Command{
	Use:   "pull [name]",
	Short: "Pull app code from the platform to the current directory",
	Args:  cobra.ExactArgs(1),
	RunE:  runPull,
}

var pullForce bool

func init() {
	pullCmd.Flags().BoolVarP(&pullForce, "force", "f", false, "Overwrite existing files")
}

func runPull(cmd *cobra.Command, args []string) error {
	appName := args[0]
	p := requirePlatform()
	client := api.NewClient(p.URL, p.Token)
	app, err := api.ResolveApp(client, appName)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}

	detail, err := client.GetApp(app["app_id"].(string))
	if err != nil {
		var pe *api.PlatformError
		if errors.As(err, &pe) {
			fmt.Fprintf(os.Stderr, "Failed to get app details: %s\n", pe.Message)
			os.Exit(1)
		}
		return err
	}

	cwd, _ := os.Getwd()
	if _, err := os.Stat(filepath.Join(cwd, project.ProjectFile)); err == nil && !pullForce {
		fmt.Fprintf(os.Stderr, "%s already exists. Use --force to overwrite.\n", project.ProjectFile)
		os.Exit(1)
	}

	mode, _ := detail["mode"].(string)
	if mode == "" {
		mode = "single"
	}
	written := 0

	if mode == "multi" {
		files, _ := detail["deployed_files"].(map[string]interface{})
		if files == nil {
			files, _ = detail["files"].(map[string]interface{})
		}
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
					written++
				}
			}
		}
	} else {
		code, _ := detail["deployed_code"].(string)
		if code == "" {
			code, _ = detail["code"].(string)
		}
		if code != "" {
			if err := os.WriteFile(filepath.Join(cwd, "app.py"), []byte(code), 0644); err != nil {
				return err
			}
			written = 1
		}
	}

	if written == 0 {
		fmt.Fprintln(os.Stderr, "App has no code to pull.")
		os.Exit(1)
	}

	entrypoint, _ := detail["entrypoint"].(string)
	if entrypoint == "" {
		entrypoint = "app.py"
	}
	name, _ := detail["name"].(string)
	if err := project.Write(cwd, &project.Project{Name: name, Entrypoint: entrypoint}); err != nil {
		return err
	}

	plural := "s"
	if written == 1 {
		plural = ""
	}
	fmt.Printf("Pulled %s (%d file%s)\n", name, written, plural)
	fmt.Printf("  Written to: %s\n", cwd)
	return nil
}
