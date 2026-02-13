package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type PlatformError struct {
	Message    string
	StatusCode int
	Code       string
}

func (e *PlatformError) Error() string {
	return e.Message
}

type Client struct {
	baseURL string
	token   string
	client  *http.Client
}

func NewClient(baseURL, token string) *Client {
	baseURL = strings.TrimSuffix(baseURL, "/")
	return &Client{
		baseURL: baseURL,
		token:   token,
		client:  &http.Client{Timeout: 30 * time.Second},
	}
}

func parseError(resp *http.Response) *PlatformError {
	body, _ := io.ReadAll(resp.Body)
	msg := string(body)
	if len(body) > 0 {
		var data struct {
			Detail interface{} `json:"detail"`
		}
		if json.Unmarshal(body, &data) == nil && data.Detail != nil {
			switch d := data.Detail.(type) {
			case string:
				msg = d
			case map[string]interface{}:
				if m, ok := d["message"].(string); ok {
					msg = m
				}
			}
		}
	}
	return &PlatformError{
		Message:    msg,
		StatusCode: resp.StatusCode,
	}
}

func (c *Client) request(method, path string, body interface{}, result interface{}) error {
	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return err
		}
		bodyReader = bytes.NewReader(b)
	}
	req, err := http.NewRequest(method, c.baseURL+path, bodyReader)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}
	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return parseError(resp)
	}
	if resp.StatusCode == 204 || result == nil {
		return nil
	}
	return json.NewDecoder(resp.Body).Decode(result)
}

func (c *Client) Login(username, password string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := c.request("POST", "/api/auth/login", map[string]string{
		"username": username,
		"password": password,
	}, &result)
	return result, err
}

func (c *Client) Me() (map[string]interface{}, error) {
	var result map[string]interface{}
	err := c.request("GET", "/api/auth/me", nil, &result)
	return result, err
}

func (c *Client) ListApps() ([]map[string]interface{}, error) {
	var result []map[string]interface{}
	err := c.request("GET", "/api/apps", nil, &result)
	return result, err
}

func (c *Client) GetApp(appID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := c.request("GET", "/api/apps/"+appID, nil, &result)
	return result, err
}

func (c *Client) CreateApp(payload map[string]interface{}) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := c.request("POST", "/api/apps", payload, &result)
	return result, err
}

func (c *Client) UpdateApp(appID string, payload map[string]interface{}) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := c.request("PUT", "/api/apps/"+appID, payload, &result)
	return result, err
}

func (c *Client) DeleteApp(appID string) error {
	return c.request("DELETE", "/api/apps/"+appID, nil, nil)
}

func (c *Client) SaveDraft(appID string, payload map[string]interface{}) error {
	return c.request("PUT", "/api/apps/"+appID+"/draft", payload, nil)
}

func (c *Client) DeployStatus(appID string) (map[string]interface{}, error) {
	var result map[string]interface{}
	err := c.request("GET", "/api/apps/"+appID+"/deploy-status", nil, &result)
	return result, err
}

func (c *Client) GetLogs(appID string, tailLines int, sinceSeconds *int) (map[string]interface{}, error) {
	path := fmt.Sprintf("/api/apps/%s/logs?tail_lines=%d", appID, tailLines)
	if sinceSeconds != nil {
		path += fmt.Sprintf("&since_seconds=%d", *sinceSeconds)
	}
	var result map[string]interface{}
	err := c.request("GET", path, nil, &result)
	return result, err
}

func (c *Client) ListTemplates() ([]map[string]interface{}, error) {
	var result []map[string]interface{}
	err := c.request("GET", "/api/templates", nil, &result)
	return result, err
}

func ResolveApp(client *Client, name string) (map[string]interface{}, error) {
	apps, err := client.ListApps()
	if err != nil {
		return nil, err
	}
	for _, a := range apps {
		if n, _ := a["name"].(string); n == name {
			return a, nil
		}
	}
	return nil, fmt.Errorf("no app named '%s' found. Run 'fp list' to see your apps", name)
}

func AppURL(platformURL, appID string) string {
	u, err := url.Parse(platformURL)
	if err != nil {
		return ""
	}
	host := u.Hostname()
	if strings.HasPrefix(host, "platform.") {
		host = strings.TrimPrefix(host, "platform.")
	}
	scheme := "https"
	if u.Scheme == "http" {
		scheme = "http"
	}
	return fmt.Sprintf("%s://app-%s.%s", scheme, appID, host)
}
