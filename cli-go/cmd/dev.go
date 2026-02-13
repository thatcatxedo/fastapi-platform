package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/spf13/cobra"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/project"
)

var devCmd = &cobra.Command{
	Use:   "dev",
	Short: "Run the app locally with hot reload",
	RunE:  runDev,
}

var devPort int

func init() {
	devCmd.Flags().IntVarP(&devPort, "port", "p", 8000, "Port to run on")
}

func runDev(cmd *cobra.Command, args []string) error {
	proj, dir, err := project.ReadFromCwd()
	if err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}

	entrypoint := proj.Entrypoint
	if entrypoint == "" {
		entrypoint = "app.py"
	}

	// app.py -> app:app, src/app.py -> src.app:app
	module := strings.TrimSuffix(entrypoint, ".py")
	module = strings.ReplaceAll(module, "/", ".")
	appRef := module + ":app"

	env := os.Environ()
	if proj.Database != nil {
		mongoURI := os.Getenv("PLATFORM_MONGO_URI")
		if mongoURI == "" {
			mongoURI = "mongodb://localhost:27017"
		}
		env = append(env, "PLATFORM_MONGO_URI="+mongoURI)
		fmt.Printf("  PLATFORM_MONGO_URI=%s\n", mongoURI)
	}

	if proj.Env != nil {
		for k, v := range proj.Env {
			if strings.HasPrefix(v, "${") && strings.HasSuffix(v, "}") {
				v = os.Getenv(v[2 : len(v)-1])
			}
			env = append(env, k+"="+v)
		}
	}

	fmt.Printf("Running %s on port %d\n", appRef, devPort)
	fmt.Println("Ctrl+C to stop")
	fmt.Println()

	uvicorn := exec.Command("python", "-m", "uvicorn", appRef,
		"--reload", "--host", "0.0.0.0", "--port", fmt.Sprintf("%d", devPort))
	uvicorn.Dir = dir
	uvicorn.Env = env
	uvicorn.Stdin = os.Stdin
	uvicorn.Stdout = os.Stdout
	uvicorn.Stderr = os.Stderr

	if err := uvicorn.Run(); err != nil {
		fmt.Fprintln(os.Stderr, "uvicorn not found. Install it: pip install uvicorn")
		os.Exit(1)
	}
	return nil
}
