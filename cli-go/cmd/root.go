package cmd

import (
	"github.com/spf13/cobra"
)

var version string

func Execute(v string) {
	version = v
	root := &cobra.Command{
		Use:   "fp",
		Short: "Deploy Python APIs from your terminal.",
		Long:  "fp — CLI for the FastAPI Platform. Deploy FastAPI and FastHTML apps from your terminal.",
	}
	root.CompletionOptions.DisableDefaultCmd = true

	root.AddCommand(authCmd)
	root.AddCommand(initCmd)
	root.AddCommand(deployCmd)
	root.AddCommand(listCmd)
	root.AddCommand(statusCmd)
	root.AddCommand(openCmd)
	root.AddCommand(deleteCmd)
	root.AddCommand(logsCmd)
	root.AddCommand(devCmd)
	root.AddCommand(pullCmd)
	root.AddCommand(pushCmd)
	root.AddCommand(versionCmd)

	if err := root.Execute(); err != nil {
		// cobra handles most errors; exit is done by commands
	}
}
