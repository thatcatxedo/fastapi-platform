package cmd

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/api"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/config"
	"golang.org/x/term"
)

var authCmd = &cobra.Command{
	Use:   "auth",
	Short: "Authentication commands",
}

var (
	authToken string
	authName  string
)

func init() {
	authCmd.AddCommand(loginCmd)
	authCmd.AddCommand(whoamiCmd)
	authCmd.AddCommand(logoutCmd)
}

var loginCmd = &cobra.Command{
	Use:   "login [platform-url]",
	Short: "Authenticate with a FastAPI Platform deployment",
	Args:  cobra.ExactArgs(1),
	RunE:  runLogin,
}

var whoamiCmd = &cobra.Command{
	Use:   "whoami",
	Short: "Show current authentication status",
	RunE:  runWhoami,
}

var logoutCmd = &cobra.Command{
	Use:   "logout",
	Short: "Remove stored credentials",
	RunE:  runLogout,
}

var logoutName string

func init() {
	loginCmd.Flags().StringVarP(&authToken, "token", "t", "", "API token for CI/headless auth")
	loginCmd.Flags().StringVarP(&authName, "name", "n", "default", "Name for this platform config")
	logoutCmd.Flags().StringVarP(&logoutName, "name", "n", "", "Platform config name to remove (default: active)")
}

func runLogin(cmd *cobra.Command, args []string) error {
	platformURL := strings.TrimSuffix(args[0], "/")
	if !strings.HasPrefix(platformURL, "http") {
		platformURL = "https://" + platformURL
	}

	if authToken != "" {
		client := api.NewClient(platformURL, authToken)
		result, err := client.Me()
		if err != nil {
			var pe *api.PlatformError
			if errors.As(err, &pe) {
				fmt.Fprintf(os.Stderr, "Authentication failed: %s\n", pe.Message)
				os.Exit(1)
			}
			return err
		}
		username, _ := result["username"].(string)
		if err := config.SavePlatform(authName, platformURL, authToken, username); err != nil {
			return err
		}
		fmt.Printf("Authenticated as %s on %s\n", username, platformURL)
		return nil
	}

	fmt.Printf("Logging in to %s\n", platformURL)
	reader := bufio.NewReader(os.Stdin)
	fmt.Print("Username: ")
	username, _ := reader.ReadString('\n')
	username = strings.TrimSpace(username)
	fmt.Print("Password: ")
	passwordBytes, err := term.ReadPassword(int(os.Stdin.Fd()))
	if err != nil {
		fmt.Print("Password: ")
		password, _ := reader.ReadString('\n')
		passwordBytes = []byte(strings.TrimSpace(password))
	} else {
		fmt.Println()
	}
	password := string(passwordBytes)

	client := api.NewClient(platformURL, "")
	result, err := client.Login(username, password)
	if err != nil {
		var pe *api.PlatformError
		if errors.As(err, &pe) {
			fmt.Fprintf(os.Stderr, "Login failed: %s\n", pe.Message)
			os.Exit(1)
		}
		return err
	}
	token, _ := result["access_token"].(string)
	if token == "" {
		fmt.Fprintln(os.Stderr, "No access token in response")
		os.Exit(1)
	}

	client = api.NewClient(platformURL, token)
	me, err := client.Me()
	if err != nil {
		var pe *api.PlatformError
		if errors.As(err, &pe) {
			fmt.Fprintf(os.Stderr, "Token verification failed: %s\n", pe.Message)
			os.Exit(1)
		}
		return err
	}
	uname, _ := me["username"].(string)
	if err := config.SavePlatform(authName, platformURL, token, uname); err != nil {
		return err
	}
	fmt.Printf("Authenticated as %s on %s\n", uname, platformURL)
	return nil
}

func runWhoami(cmd *cobra.Command, args []string) error {
	name, p := config.GetActivePlatformWithName()
	if p == nil {
		fmt.Fprintln(os.Stderr, "Not authenticated. Run 'fp auth login <platform-url>' first.")
		os.Exit(1)
	}
	client := api.NewClient(p.URL, p.Token)
	user, err := client.Me()
	if err != nil {
		var pe *api.PlatformError
		if errors.As(err, &pe) {
			fmt.Fprintf(os.Stderr, "Token expired or invalid: %s\n", pe.Message)
			fmt.Fprintln(os.Stderr, "Run 'fp auth login <platform-url>' to re-authenticate.")
			os.Exit(1)
		}
		return err
	}
	username, _ := user["username"].(string)
	email, _ := user["email"].(string)
	if email == "" {
		email = "n/a"
	}
	fmt.Printf("  User:     %s\n", username)
	fmt.Printf("  Email:    %s\n", email)
	fmt.Printf("  Platform: %s\n", p.URL)
	fmt.Printf("  Config:   %s\n", name)
	if isAdmin, _ := user["is_admin"].(bool); isAdmin {
		fmt.Println("  Role:     admin")
	}
	return nil
}

func runLogout(cmd *cobra.Command, args []string) error {
	name := logoutName
	if name == "" {
		n, _ := config.GetActivePlatformWithName()
		name = n
	}
	if name == "" {
		fmt.Fprintln(os.Stderr, "No active platform to log out from.")
		return nil
	}
	if config.RemovePlatform(name) {
		fmt.Printf("Logged out from %s\n", name)
	} else {
		fmt.Fprintf(os.Stderr, "No platform config named '%s' found.\n", name)
	}
	return nil
}
