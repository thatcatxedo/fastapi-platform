package cmd

import (
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/api"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/config"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/project"
)

var deployCmd = &cobra.Command{
	Use:   "deploy",
	Short: "Deploy the current project to the platform",
	RunE:  runDeploy,
}

var phaseLabels = map[string]string{
	"validating":         "Validating code...",
	"creating_resources": "Creating Kubernetes resources...",
	"pending":            "Waiting to be scheduled...",
	"scheduled":          "Pod scheduled...",
	"pulling":            "Pulling container image...",
	"pulled":             "Image pulled...",
	"creating":           "Creating container...",
	"starting":           "Starting application...",
	"ready":              "Application ready!",
	"error":              "Deployment error",
}

func runDeploy(cmd *cobra.Command, args []string) error {
	proj, dir, err := project.ReadFromCwd()
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
	if proj.Name == "" {
		fmt.Fprintln(os.Stderr, "No 'name' field in .fp.yaml")
		os.Exit(1)
	}

	p := config.GetActivePlatform()
	if p == nil {
		fmt.Fprintln(os.Stderr, "Not authenticated. Run 'fp auth login <platform-url>' first.")
		os.Exit(1)
	}

	entrypoint := proj.Entrypoint
	if entrypoint == "" {
		entrypoint = "app.py"
	}

	files, err := project.CollectFiles(dir, entrypoint)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}

	mode := project.DetectMode(files)
	client := api.NewClient(p.URL, p.Token)

	fmt.Printf("Deploying %s to %s\n", proj.Name, p.URL)
	if mode == "multi" {
		fmt.Printf("  %d files, mode: multi-file\n", len(files))
	} else {
		fmt.Println("  mode: single-file")
	}

	apps, err := client.ListApps()
	if err != nil {
		return err
	}
	var existing map[string]interface{}
	for _, a := range apps {
		if n, _ := a["name"].(string); n == proj.Name {
			existing = a
			break
		}
	}

	payload := make(map[string]interface{})
	payload["name"] = proj.Name
	if mode == "multi" {
		payload["files"] = files
		payload["mode"] = "multi"
		payload["entrypoint"] = entrypoint
	} else {
		payload["code"] = files[entrypoint]
		payload["mode"] = "single"
	}

	if proj.Env != nil {
		resolved := make(map[string]string)
		for k, v := range proj.Env {
			if strings.HasPrefix(v, "${") && strings.HasSuffix(v, "}") {
				resolved[k] = os.Getenv(v[2 : len(v)-1])
			} else {
				resolved[k] = v
			}
		}
		payload["env_vars"] = resolved
	}

	var result map[string]interface{}
	if existing != nil {
		appID, _ := existing["app_id"].(string)
		result, err = client.UpdateApp(appID, payload)
		if err != nil {
			return handleAPIError(err)
		}
		fmt.Printf("  Updating existing app (%s)\n", appID)
	} else {
		result, err = client.CreateApp(payload)
		if err != nil {
			return handleAPIError(err)
		}
		appID, _ := result["app_id"].(string)
		fmt.Printf("  Created new app (%s)\n", appID)
	}

	appID, _ := result["app_id"].(string)
	if appID == "" && existing != nil {
		appID, _ = existing["app_id"].(string)
	}
	if appID == "" {
		fmt.Fprintln(os.Stderr, "No app_id in response")
		os.Exit(1)
	}

	// Poll deploy status
	for i := 0; i < 60; i++ {
		status, err := client.DeployStatus(appID)
		if err != nil {
			time.Sleep(2 * time.Second)
			continue
		}

		phase := "creating_resources"
		if ready, _ := status["deployment_ready"].(bool); ready {
			phase = "ready"
		} else if s, _ := status["status"].(string); s == "error" {
			phase = "error"
		} else if stage, ok := status["deploy_stage"].(string); ok {
			phase = stage
		}

		label := phaseLabels[phase]
		if label == "" {
			label = phase
		}
		fmt.Printf("\r%s", label)

		if phase == "ready" {
			break
		}
		if phase == "error" {
			lastErr, _ := status["last_error"].(string)
			if lastErr == "" {
				lastErr = "Unknown error"
			}
			fmt.Fprintf(os.Stderr, "\nDeployment failed: %s\n", lastErr)
			os.Exit(1)
		}

		time.Sleep(2 * time.Second)
	}

	appURL := api.AppURL(p.URL, appID)
	fmt.Println()
	fmt.Println("Deployed successfully!")
	fmt.Printf("  URL:  %s\n", appURL)
	fmt.Printf("  Docs: %s/docs\n", appURL)
	return nil
}

func handleAPIError(err error) error {
	var pe *api.PlatformError
	if errors.As(err, &pe) {
		fmt.Fprintf(os.Stderr, "\nDeploy failed: %s\n", pe.Message)
		os.Exit(1)
	}
	return err
}
