package cmd

import (
	"errors"
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/api"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/project"
)

var pushCmd = &cobra.Command{
	Use:   "push",
	Short: "Push local code to the platform as a draft (no deploy)",
	RunE:  runPush,
}

func runPush(cmd *cobra.Command, args []string) error {
	proj, dir, err := project.ReadFromCwd()
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
	if proj.Name == "" {
		fmt.Fprintln(os.Stderr, "No 'name' field in .fp.yaml")
		os.Exit(1)
	}

	entrypoint := proj.Entrypoint
	if entrypoint == "" {
		entrypoint = "app.py"
	}

	p := requirePlatform()
	client := api.NewClient(p.URL, p.Token)
	app, err := api.ResolveApp(client, proj.Name)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}

	files, err := project.CollectFiles(dir, entrypoint)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}

	mode := project.DetectMode(files)
	payload := make(map[string]interface{})
	if mode == "multi" {
		payload["files"] = files
	} else {
		payload["code"] = files[entrypoint]
	}

	appID, _ := app["app_id"].(string)
	if err := client.SaveDraft(appID, payload); err != nil {
		var pe *api.PlatformError
		if errors.As(err, &pe) {
			fmt.Fprintf(os.Stderr, "Push failed: %s\n", pe.Message)
			os.Exit(1)
		}
		return err
	}

	plural := "s"
	if len(files) == 1 {
		plural = ""
	}
	fmt.Printf("Pushed draft for %s (%d file%s)\n", proj.Name, len(files), plural)
	fmt.Println("  Run 'fp deploy' to publish these changes.")
	return nil
}
