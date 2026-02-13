package main

import (
	"github.com/thatcatxedo/fastapi-platform/cli-go/cmd"
)

var Version = "0.1.0"

func main() {
	cmd.Execute(Version)
}
