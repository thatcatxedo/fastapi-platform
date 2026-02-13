package cmd

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/url"
	"os"
	"regexp"
	"strings"

	"github.com/gorilla/websocket"
	"github.com/spf13/cobra"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/api"
	"github.com/thatcatxedo/fastapi-platform/cli-go/internal/config"
)

var logsCmd = &cobra.Command{
	Use:   "logs [name]",
	Short: "Tail app logs",
	Args:  cobra.MaximumNArgs(1),
	RunE:  runLogs,
}

var (
	logsFollow   bool
	logsNoFollow bool
	logsSince    string
	logsTail     int
)

func init() {
	logsCmd.Flags().BoolVarP(&logsFollow, "follow", "f", true, "Stream logs in real-time")
	logsCmd.Flags().BoolVar(&logsNoFollow, "no-follow", false, "Fetch recent logs only (no stream)")
	logsCmd.Flags().StringVarP(&logsSince, "since", "s", "", "Only logs since (e.g. 30s, 5m, 1h)")
	logsCmd.Flags().IntVarP(&logsTail, "tail", "n", 100, "Number of recent lines")
}

func parseSince(s string) (int, error) {
	re := regexp.MustCompile(`^(\d+)([smh])$`)
	m := re.FindStringSubmatch(strings.TrimSpace(s))
	if m == nil {
		return 0, fmt.Errorf("invalid --since format: '%s'. Use e.g. 30s, 5m, 1h", s)
	}
	var value int
	fmt.Sscanf(m[1], "%d", &value)
	multiplier := map[string]int{"s": 1, "m": 60, "h": 3600}
	return value * multiplier[m[2]], nil
}

func runLogs(cmd *cobra.Command, args []string) error {
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

	if logsFollow && !logsNoFollow && logsSince == "" {
		streamLogsWS(p.URL, p.Token, appID)
		return nil
	}

	var sinceSeconds *int
	if logsSince != "" {
		s, err := parseSince(logsSince)
		if err != nil {
			fmt.Fprintln(os.Stderr, err.Error())
			os.Exit(1)
		}
		sinceSeconds = &s
	}

	data, err := client.GetLogs(appID, logsTail, sinceSeconds)
	if err != nil {
		var pe *api.PlatformError
		if errors.As(err, &pe) {
			fmt.Fprintf(os.Stderr, "Failed to fetch logs: %s\n", pe.Message)
			os.Exit(1)
		}
		return err
	}

	logLines, _ := data["logs"].([]interface{})
	if len(logLines) == 0 {
		fmt.Println("No logs available.")
		return nil
	}

	for _, line := range logLines {
		m, _ := line.(map[string]interface{})
		ts, _ := m["timestamp"].(string)
		msg, _ := m["message"].(string)
		if ts != "" {
			fmt.Printf("%s %s\n", ts, msg)
		} else {
			fmt.Println(msg)
		}
	}
	return nil
}

func streamLogsWS(platformURL, token, appID string) {
	wsURL := strings.Replace(platformURL, "https://", "wss://", 1)
	wsURL = strings.Replace(wsURL, "http://", "ws://", 1)
	wsURL = wsURL + "/api/apps/" + appID + "/logs/stream?token=" + url.QueryEscape(token)

	fmt.Println("Streaming logs (Ctrl+C to stop)...")

	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		fmt.Fprintf(os.Stderr, "WebSocket error: %v\n", err)
		fmt.Println("Falling back to HTTP logs...")
		p := config.GetActivePlatform()
		if p != nil {
			client := api.NewClient(p.URL, p.Token)
			data, _ := client.GetLogs(appID, 50, nil)
			if logs, _ := data["logs"].([]interface{}); len(logs) > 0 {
				for _, line := range logs {
					m, _ := line.(map[string]interface{})
					ts, _ := m["timestamp"].(string)
					msg, _ := m["message"].(string)
					if ts != "" {
						fmt.Printf("%s %s\n", ts, msg)
					} else {
						fmt.Println(msg)
					}
				}
			}
		}
		return
	}
	defer conn.Close()

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			return
		}
		var data map[string]interface{}
		if json.Unmarshal(message, &data) != nil {
			fmt.Println(string(message))
			continue
		}
		msgType, _ := data["type"].(string)
		switch msgType {
		case "log":
			ts, _ := data["timestamp"].(string)
			msg, _ := data["message"].(string)
			if ts != "" {
				fmt.Printf("%s %s\n", ts, msg)
			} else {
				fmt.Println(msg)
			}
		case "connected":
			podName, _ := data["pod_name"].(string)
			fmt.Printf("Connected to pod: %s\n", podName)
		case "status":
			msg, _ := data["message"].(string)
			fmt.Println(msg)
		case "error":
			msg, _ := data["message"].(string)
			fmt.Fprintf(os.Stderr, "%s\n", msg)
		}
	}
}
