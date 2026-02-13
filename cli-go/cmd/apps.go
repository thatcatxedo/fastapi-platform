package cmd

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"strings"

	"github.com/spf13/cobra"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/api"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/config"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/project"
)

var listCmd = &cobra.Command{
	Use:   "list",
	Short: "List all your apps",
	RunE:  runList,
}

var statusCmd = &cobra.Command{
	Use:   "status [name]",
	Short: "Show app status",
	Args:  cobra.MaximumNArgs(1),
	RunE:  runStatus,
}

var openCmd = &cobra.Command{
	Use:   "open [name]",
	Short: "Open app URL in browser",
	Args:  cobra.MaximumNArgs(1),
	RunE:  runOpen,
}

var deleteCmd = &cobra.Command{
	Use:   "delete [name]",
	Short: "Delete an app",
	Args:  cobra.ExactArgs(1),
	RunE:  runDelete,
}

var deleteYes bool

func init() {
	deleteCmd.Flags().BoolVarP(&deleteYes, "yes", "y", false, "Skip confirmation")
}

func requirePlatform() *config.Platform {
	p := config.GetActivePlatform()
	if p == nil {
		fmt.Fprintln(os.Stderr, "Not authenticated. Run 'fp auth login <platform-url>' first.")
		os.Exit(1)
	}
	return p
}

func resolveAppName(name string) string {
	if name != "" {
		return name
	}
	fp, ok := project.FindProjectFile("")
	if !ok {
		fmt.Fprintln(os.Stderr, "No app name provided and no .fp.yaml found.")
		os.Exit(1)
	}
	proj, err := project.Read(fp)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
	if proj.Name == "" {
		fmt.Fprintln(os.Stderr, "No app name in .fp.yaml")
		os.Exit(1)
	}
	return proj.Name
}

func runList(cmd *cobra.Command, args []string) error {
	p := requirePlatform()
	client := api.NewClient(p.URL, p.Token)
	apps, err := client.ListApps()
	if err != nil {
		var pe *api.PlatformError
		if errors.As(err, &pe) {
			fmt.Fprintf(os.Stderr, "Failed to list apps: %s\n", pe.Message)
			os.Exit(1)
		}
		return err
	}
	if len(apps) == 0 {
		fmt.Println("No apps yet. Run 'fp init' + 'fp deploy' to create one.")
		return nil
	}

	// Table
	fmt.Printf("%-20s %-10s %-40s %-12s\n", "Name", "Status", "URL", "Last Deploy")
	fmt.Println(strings.Repeat("-", 85))
	for _, a := range apps {
		name, _ := a["name"].(string)
		status, _ := a["status"].(string)
		appID, _ := a["app_id"].(string)
		url := api.AppURL(p.URL, appID)
		lastDeploy, _ := a["last_deploy_at"].(string)
		if lastDeploy == "" {
			lastDeploy, _ = a["created_at"].(string)
		}
		if idx := strings.Index(lastDeploy, "T"); idx > 0 {
			lastDeploy = lastDeploy[:idx]
		}
		if len(url) > 38 {
			url = url[:35] + "..."
		}
		fmt.Printf("%-20s %-10s %-40s %-12s\n", name, status, url, lastDeploy)
	}
	return nil
}

func runStatus(cmd *cobra.Command, args []string) error {
	appName := resolveAppName("")
	if len(args) > 0 {
		appName = args[0]
	}
	p := requirePlatform()
	client := api.NewClient(p.URL, p.Token)
	app, err := api.ResolveApp(client, appName)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
	appID, _ := app["app_id"].(string)
	appURL := api.AppURL(p.URL, appID)

	ds, _ := client.DeployStatus(appID)
	appStatus, _ := ds["status"].(string)
	if appStatus == "" {
		appStatus, _ = app["status"].(string)
	}
	if appStatus == "" {
		appStatus = "unknown"
	}
	ready, _ := ds["deployment_ready"].(bool)

	style := "dim"
	if appStatus == "running" && ready {
		style = "green"
	} else if appStatus == "deploying" {
		style = "yellow"
	} else if appStatus == "error" || appStatus == "failed" {
		style = "red"
	}

	fmt.Printf("  Name:   %s\n", app["name"])
	fmt.Printf("  Status: %s\n", appStatus)
	fmt.Printf("  Ready:  %v\n", ready)
	fmt.Printf("  URL:    %s\n", appURL)
	fmt.Printf("  ID:     %s\n", appID)
	if lastErr, _ := ds["last_error"].(string); lastErr != "" {
		fmt.Printf("  Error:  %s\n", lastErr)
	}
	_ = style
	return nil
}

func runOpen(cmd *cobra.Command, args []string) error {
	appName := resolveAppName("")
	if len(args) > 0 {
		appName = args[0]
	}
	p := requirePlatform()
	client := api.NewClient(p.URL, p.Token)
	app, err := api.ResolveApp(client, appName)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
	appID, _ := app["app_id"].(string)
	appURL := api.AppURL(p.URL, appID)
	fmt.Printf("Opening %s\n", appURL)

	var openCmd *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		openCmd = exec.Command("open", appURL)
	case "windows":
		openCmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", appURL)
	default:
		openCmd = exec.Command("xdg-open", appURL)
	}
	return openCmd.Start()
}

func runDelete(cmd *cobra.Command, args []string) error {
	appName := args[0]
	p := requirePlatform()
	client := api.NewClient(p.URL, p.Token)
	app, err := api.ResolveApp(client, appName)
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
	if !deleteYes {
		fmt.Printf("Delete app '%s'? This cannot be undone [y/N]: ", app["name"])
		var confirm string
		fmt.Scanln(&confirm)
		if !strings.EqualFold(strings.TrimSpace(confirm), "y") {
			return nil
		}
	}
	appID, _ := app["app_id"].(string)
	if err := client.DeleteApp(appID); err != nil {
		var pe *api.PlatformError
		if errors.As(err, &pe) {
			fmt.Fprintf(os.Stderr, "Delete failed: %s\n", pe.Message)
			os.Exit(1)
		}
		return err
	}
	fmt.Printf("Deleted %s\n", app["name"])
	return nil
}
