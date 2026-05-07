"""Go (Golang) reference patterns — basics through advanced.

Covers project setup, HTTP frameworks (net/http, gin, echo, fiber), DB access
(database/sql, GORM), concurrency, errors, context, observability, testing,
gRPC, Docker, and common idioms. Indexed by natural-language request.
"""
from __future__ import annotations


GOLANG_SEED: list[dict] = [

# ───────── Project setup ─────────
{
    "request": "create a new Go project from scratch",
    "language": "bash", "framework": "golang",
    "code": """mkdir my-app && cd my-app
go mod init github.com/you/my-app
mkdir -p cmd/server internal/handler internal/store
touch cmd/server/main.go
go run ./cmd/server""",
},
{
    "request": "Go project layout following standard conventions",
    "language": "text", "framework": "golang",
    "code": """my-app/
├── go.mod                # module + dep tracking
├── go.sum                # checksums
├── cmd/                  # main entry points
│   └── server/main.go    # the binary
├── internal/             # private packages — not importable externally
│   ├── handler/          # HTTP handlers
│   ├── store/            # DB access
│   └── service/          # business logic
├── pkg/                  # public reusable packages (only if you mean it)
├── api/                  # OpenAPI / proto files
├── configs/              # config files
├── Dockerfile
└── Makefile""",
},
{
    "request": "Go Makefile for build run test",
    "language": "make", "framework": "golang",
    "code": """.PHONY: build run test lint clean

build:
\tgo build -o bin/server ./cmd/server

run:
\tgo run ./cmd/server

test:
\tgo test ./... -race -cover

lint:
\tgolangci-lint run

clean:
\trm -rf bin/""",
},

# ───────── HTTP servers ─────────
{
    "request": "Go hello world HTTP server using net/http",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"fmt"
\t"log"
\t"net/http"
)

func main() {
\tmux := http.NewServeMux()
\tmux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
\t\tfmt.Fprintln(w, "hello, world")
\t})
\tlog.Println("listening on :8080")
\tlog.Fatal(http.ListenAndServe(":8080", mux))
}""",
},
{
    "request": "Go HTTP server with Gin and route groups",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"net/http"

\t"github.com/gin-gonic/gin"
)

func main() {
\tr := gin.Default()

\tr.GET("/health", func(c *gin.Context) { c.JSON(200, gin.H{"ok": true}) })

\tapi := r.Group("/api/v1")
\t{
\t\tapi.GET("/users", listUsers)
\t\tapi.POST("/users", createUser)
\t\tapi.GET("/users/:id", getUser)
\t}

\tr.Run(":8080")
}

func listUsers(c *gin.Context)  { c.JSON(http.StatusOK, gin.H{"users": []any{}}) }
func createUser(c *gin.Context) { c.JSON(http.StatusCreated, gin.H{"id": 1}) }
func getUser(c *gin.Context)    { c.JSON(http.StatusOK, gin.H{"id": c.Param("id")}) }""",
},
{
    "request": "Go Echo framework with middleware and JSON binding",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"net/http"

\t"github.com/labstack/echo/v4"
\t"github.com/labstack/echo/v4/middleware"
)

type CreateUser struct {
\tName  string `json:"name" validate:"required"`
\tEmail string `json:"email" validate:"required,email"`
}

func main() {
\te := echo.New()
\te.Use(middleware.Logger())
\te.Use(middleware.Recover())
\te.Use(middleware.CORS())

\te.POST("/users", func(c echo.Context) error {
\t\tvar in CreateUser
\t\tif err := c.Bind(&in); err != nil {
\t\t\treturn echo.NewHTTPError(http.StatusBadRequest, err.Error())
\t\t}
\t\treturn c.JSON(http.StatusCreated, map[string]any{"id": 1, "name": in.Name})
\t})

\te.Logger.Fatal(e.Start(":8080"))
}""",
},
{
    "request": "Go Fiber high-performance server",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"github.com/gofiber/fiber/v2"
\t"github.com/gofiber/fiber/v2/middleware/logger"
\t"github.com/gofiber/fiber/v2/middleware/recover"
)

func main() {
\tapp := fiber.New(fiber.Config{
\t\tAppName: "my-api",
\t})
\tapp.Use(logger.New())
\tapp.Use(recover.New())

\tapp.Get("/health", func(c *fiber.Ctx) error {
\t\treturn c.JSON(fiber.Map{"ok": true})
\t})

\tapp.Get("/users/:id", func(c *fiber.Ctx) error {
\t\treturn c.JSON(fiber.Map{"id": c.Params("id")})
\t})

\tapp.Listen(":8080")
}""",
},
{
    "request": "Go HTTP middleware pattern with net/http",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"log"
\t"net/http"
\t"time"
)

func logging(next http.Handler) http.Handler {
\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
\t\tstart := time.Now()
\t\tnext.ServeHTTP(w, r)
\t\tlog.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(start))
\t})
}

func cors(next http.Handler) http.Handler {
\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
\t\tw.Header().Set("Access-Control-Allow-Origin", "*")
\t\tnext.ServeHTTP(w, r)
\t})
}

func main() {
\tmux := http.NewServeMux()
\tmux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
\t\tw.Write([]byte("ok"))
\t})

\thandler := logging(cors(mux))
\thttp.ListenAndServe(":8080", handler)
}""",
},
{
    "request": "Go JSON request and response with struct tags",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"encoding/json"
\t"net/http"
)

type User struct {
\tID    int    `json:"id"`
\tName  string `json:"name"`
\tEmail string `json:"email,omitempty"`
}

func handleUser(w http.ResponseWriter, r *http.Request) {
\tvar u User
\tif err := json.NewDecoder(r.Body).Decode(&u); err != nil {
\t\thttp.Error(w, err.Error(), http.StatusBadRequest)
\t\treturn
\t}
\tu.ID = 42

\tw.Header().Set("Content-Type", "application/json")
\tjson.NewEncoder(w).Encode(u)
}""",
},
{
    "request": "Go graceful shutdown for HTTP server",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"context"
\t"log"
\t"net/http"
\t"os"
\t"os/signal"
\t"syscall"
\t"time"
)

func main() {
\tsrv := &http.Server{Addr: ":8080", Handler: nil}

\tgo func() {
\t\tif err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
\t\t\tlog.Fatalf("listen: %v", err)
\t\t}
\t}()
\tlog.Println("server started")

\tquit := make(chan os.Signal, 1)
\tsignal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
\t<-quit
\tlog.Println("shutdown signal received")

\tctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
\tdefer cancel()
\tif err := srv.Shutdown(ctx); err != nil {
\t\tlog.Fatalf("forced shutdown: %v", err)
\t}
\tlog.Println("server stopped cleanly")
}""",
},

# ───────── Database ─────────
{
    "request": "Go database/sql with Postgres CRUD",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"database/sql"
\t"log"

\t_ "github.com/lib/pq"
)

type User struct {
\tID    int
\tName  string
\tEmail string
}

func openDB(dsn string) (*sql.DB, error) {
\tdb, err := sql.Open("postgres", dsn)
\tif err != nil {
\t\treturn nil, err
\t}
\tdb.SetMaxOpenConns(25)
\tdb.SetMaxIdleConns(5)
\treturn db, db.Ping()
}

func createUser(db *sql.DB, u *User) error {
\treturn db.QueryRow(
\t\t`INSERT INTO users(name,email) VALUES($1,$2) RETURNING id`,
\t\tu.Name, u.Email,
\t).Scan(&u.ID)
}

func getUser(db *sql.DB, id int) (*User, error) {
\tu := &User{}
\terr := db.QueryRow(
\t\t`SELECT id,name,email FROM users WHERE id=$1`, id,
\t).Scan(&u.ID, &u.Name, &u.Email)
\tif err == sql.ErrNoRows {
\t\treturn nil, nil
\t}
\treturn u, err
}

func listUsers(db *sql.DB) ([]User, error) {
\trows, err := db.Query(`SELECT id,name,email FROM users ORDER BY id`)
\tif err != nil {
\t\treturn nil, err
\t}
\tdefer rows.Close()
\tvar out []User
\tfor rows.Next() {
\t\tvar u User
\t\tif err := rows.Scan(&u.ID, &u.Name, &u.Email); err != nil {
\t\t\treturn nil, err
\t\t}
\t\tout = append(out, u)
\t}
\treturn out, rows.Err()
}

func main() {
\tdb, err := openDB("postgres://user:pass@localhost/mydb?sslmode=disable")
\tif err != nil {
\t\tlog.Fatal(err)
\t}
\tdefer db.Close()
}""",
},
{
    "request": "Go GORM model with relationships and CRUD",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"gorm.io/driver/postgres"
\t"gorm.io/gorm"
)

type User struct {
\tID    uint   `gorm:"primaryKey"`
\tName  string `gorm:"size:100;not null"`
\tEmail string `gorm:"uniqueIndex;not null"`
\tPosts []Post
}

type Post struct {
\tID     uint   `gorm:"primaryKey"`
\tTitle  string
\tBody   string
\tUserID uint
}

func main() {
\tdsn := "host=localhost user=u password=p dbname=mydb sslmode=disable"
\tdb, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
\tif err != nil {
\t\tpanic(err)
\t}
\tdb.AutoMigrate(&User{}, &Post{})

\tu := &User{Name: "Ada", Email: "ada@example.com"}
\tdb.Create(u)

\tdb.Model(u).Association("Posts").Append(&Post{Title: "hello", Body: "world"})

\tvar got User
\tdb.Preload("Posts").First(&got, u.ID)
}""",
},

# ───────── Concurrency ─────────
{
    "request": "Go goroutines and channels basic example",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"fmt"
\t"sync"
)

func main() {
\tnums := []int{1, 2, 3, 4, 5}
\tresults := make(chan int, len(nums))
\tvar wg sync.WaitGroup

\tfor _, n := range nums {
\t\twg.Add(1)
\t\tgo func(x int) {
\t\t\tdefer wg.Done()
\t\t\tresults <- x * x
\t\t}(n)
\t}

\tgo func() { wg.Wait(); close(results) }()

\tfor sq := range results {
\t\tfmt.Println(sq)
\t}
}""",
},
{
    "request": "Go worker pool pattern",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"fmt"
\t"sync"
\t"time"
)

func worker(id int, jobs <-chan int, results chan<- int, wg *sync.WaitGroup) {
\tdefer wg.Done()
\tfor j := range jobs {
\t\ttime.Sleep(100 * time.Millisecond) // simulate work
\t\tresults <- j * 2
\t\tfmt.Printf("worker %d processed %d\\n", id, j)
\t}
}

func main() {
\tjobs := make(chan int, 100)
\tresults := make(chan int, 100)
\tvar wg sync.WaitGroup

\tfor w := 1; w <= 3; w++ {
\t\twg.Add(1)
\t\tgo worker(w, jobs, results, &wg)
\t}

\tfor j := 1; j <= 9; j++ {
\t\tjobs <- j
\t}
\tclose(jobs)

\twg.Wait()
\tclose(results)

\tfor r := range results {
\t\tfmt.Println("result:", r)
\t}
}""",
},
{
    "request": "Go context cancellation with timeout",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"context"
\t"fmt"
\t"time"
)

func slowOp(ctx context.Context) error {
\tselect {
\tcase <-time.After(2 * time.Second):
\t\treturn nil
\tcase <-ctx.Done():
\t\treturn ctx.Err()
\t}
}

func main() {
\tctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
\tdefer cancel()

\tif err := slowOp(ctx); err != nil {
\t\tfmt.Println("aborted:", err)
\t} else {
\t\tfmt.Println("completed")
\t}
}""",
},
{
    "request": "Go sync.Mutex for shared counter",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"fmt"
\t"sync"
)

type Counter struct {
\tmu sync.Mutex
\tn  int
}

func (c *Counter) Inc() {
\tc.mu.Lock()
\tdefer c.mu.Unlock()
\tc.n++
}

func (c *Counter) Value() int {
\tc.mu.Lock()
\tdefer c.mu.Unlock()
\treturn c.n
}

func main() {
\tc := &Counter{}
\tvar wg sync.WaitGroup
\tfor i := 0; i < 1000; i++ {
\t\twg.Add(1)
\t\tgo func() { defer wg.Done(); c.Inc() }()
\t}
\twg.Wait()
\tfmt.Println(c.Value()) // 1000
}""",
},

# ───────── Errors ─────────
{
    "request": "Go custom error types with errors.Is and errors.As",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"errors"
\t"fmt"
)

type NotFoundError struct {
\tResource string
\tID       string
}

func (e *NotFoundError) Error() string {
\treturn fmt.Sprintf("%s %q not found", e.Resource, e.ID)
}

var ErrUnauthorized = errors.New("unauthorized")

func fetchUser(id string) error {
\tif id == "" {
\t\treturn ErrUnauthorized
\t}
\treturn &NotFoundError{Resource: "user", ID: id}
}

func main() {
\terr := fetchUser("42")

\tvar nf *NotFoundError
\tif errors.As(err, &nf) {
\t\tfmt.Println("missing:", nf.Resource, nf.ID)
\t}

\tif errors.Is(err, ErrUnauthorized) {
\t\tfmt.Println("auth failure")
\t}
}""",
},
{
    "request": "Go error wrapping with fmt.Errorf and %w",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"errors"
\t"fmt"
\t"os"
)

var ErrConfigMissing = errors.New("config missing")

func loadConfig(path string) error {
\t_, err := os.Open(path)
\tif err != nil {
\t\treturn fmt.Errorf("loadConfig: %w", err)
\t}
\treturn nil
}

func main() {
\terr := loadConfig("/nope")
\tif err != nil {
\t\tfmt.Println(err)
\t\tif errors.Is(err, os.ErrNotExist) {
\t\t\tfmt.Println("→ file genuinely doesn't exist")
\t\t}
\t}
}""",
},

# ───────── Auth & middleware ─────────
{
    "request": "Go JWT auth middleware with golang-jwt",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"net/http"
\t"strings"
\t"time"

\t"github.com/golang-jwt/jwt/v5"
)

var jwtSecret = []byte("change-me-in-prod")

type Claims struct {
\tUserID int    `json:"uid"`
\tEmail  string `json:"email"`
\tjwt.RegisteredClaims
}

func issue(uid int, email string) (string, error) {
\tc := Claims{
\t\tUserID: uid, Email: email,
\t\tRegisteredClaims: jwt.RegisteredClaims{
\t\t\tExpiresAt: jwt.NewNumericDate(time.Now().Add(24 * time.Hour)),
\t\t},
\t}
\treturn jwt.NewWithClaims(jwt.SigningMethodHS256, c).SignedString(jwtSecret)
}

func authMiddleware(next http.Handler) http.Handler {
\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
\t\thdr := r.Header.Get("Authorization")
\t\ttoken := strings.TrimPrefix(hdr, "Bearer ")
\t\tif token == hdr {
\t\t\thttp.Error(w, "missing bearer", http.StatusUnauthorized)
\t\t\treturn
\t\t}
\t\tclaims := &Claims{}
\t\t_, err := jwt.ParseWithClaims(token, claims, func(t *jwt.Token) (any, error) {
\t\t\treturn jwtSecret, nil
\t\t})
\t\tif err != nil {
\t\t\thttp.Error(w, "invalid token", http.StatusUnauthorized)
\t\t\treturn
\t\t}
\t\tnext.ServeHTTP(w, r)
\t})
}""",
},

# ───────── Logging & config ─────────
{
    "request": "Go structured logging with slog",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"log/slog"
\t"os"
)

func main() {
\tlogger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
\t\tLevel: slog.LevelDebug,
\t}))
\tslog.SetDefault(logger)

\tslog.Info("server starting", "port", 8080, "env", "prod")
\tslog.Warn("slow query", "duration_ms", 1240, "table", "users")
\tslog.Error("failed", "err", "connection refused", "host", "db.local")

\t// scoped logger
\treq := logger.With("request_id", "r-42")
\treq.Info("incoming", "path", "/api/users")
}""",
},
{
    "request": "Go config loading with viper",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"fmt"

\t"github.com/spf13/viper"
)

type Config struct {
\tPort     int    `mapstructure:"port"`
\tDBURL    string `mapstructure:"db_url"`
\tLogLevel string `mapstructure:"log_level"`
}

func loadConfig() (*Config, error) {
\tviper.SetConfigName("config")
\tviper.SetConfigType("yaml")
\tviper.AddConfigPath(".")
\tviper.AddConfigPath("./configs")

\tviper.AutomaticEnv() // overrides via env vars
\tviper.SetDefault("port", 8080)
\tviper.SetDefault("log_level", "info")

\tif err := viper.ReadInConfig(); err != nil {
\t\treturn nil, fmt.Errorf("read config: %w", err)
\t}

\tvar c Config
\tif err := viper.Unmarshal(&c); err != nil {
\t\treturn nil, err
\t}
\treturn &c, nil
}""",
},

# ───────── Testing ─────────
{
    "request": "Go table-driven tests",
    "language": "go", "framework": "golang",
    "code": """package math_test

import "testing"

func add(a, b int) int { return a + b }

func TestAdd(t *testing.T) {
\ttests := []struct {
\t\tname    string
\t\ta, b    int
\t\twantSum int
\t}{
\t\t{"zeros", 0, 0, 0},
\t\t{"positives", 2, 3, 5},
\t\t{"negative", -1, 1, 0},
\t\t{"big", 1_000_000, 2_000_000, 3_000_000},
\t}

\tfor _, tt := range tests {
\t\tt.Run(tt.name, func(t *testing.T) {
\t\t\tif got := add(tt.a, tt.b); got != tt.wantSum {
\t\t\t\tt.Errorf("add(%d,%d)=%d, want %d", tt.a, tt.b, got, tt.wantSum)
\t\t\t}
\t\t})
\t}
}""",
},
{
    "request": "Go HTTP handler test with httptest",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"net/http"
\t"net/http/httptest"
\t"strings"
\t"testing"
)

func helloHandler(w http.ResponseWriter, r *http.Request) {
\tw.Write([]byte("hello, " + r.URL.Query().Get("name")))
}

func TestHelloHandler(t *testing.T) {
\treq := httptest.NewRequest(http.MethodGet, "/hello?name=Ada", nil)
\trr := httptest.NewRecorder()

\thelloHandler(rr, req)

\tif rr.Code != http.StatusOK {
\t\tt.Fatalf("status = %d, want 200", rr.Code)
\t}
\tif !strings.Contains(rr.Body.String(), "Ada") {
\t\tt.Errorf("body = %q, want it to contain Ada", rr.Body.String())
\t}
}""",
},
{
    "request": "Go testify assertions and mocks",
    "language": "go", "framework": "golang",
    "code": """package svc_test

import (
\t"errors"
\t"testing"

\t"github.com/stretchr/testify/assert"
\t"github.com/stretchr/testify/mock"
\t"github.com/stretchr/testify/require"
)

type Repo interface {
\tFind(id int) (string, error)
}

type RepoMock struct{ mock.Mock }

func (m *RepoMock) Find(id int) (string, error) {
\targs := m.Called(id)
\treturn args.String(0), args.Error(1)
}

func TestSomething(t *testing.T) {
\trepo := &RepoMock{}
\trepo.On("Find", 1).Return("Ada", nil)
\trepo.On("Find", 99).Return("", errors.New("not found"))

\tname, err := repo.Find(1)
\trequire.NoError(t, err)
\tassert.Equal(t, "Ada", name)

\t_, err = repo.Find(99)
\tassert.Error(t, err)

\trepo.AssertExpectations(t)
}""",
},

# ───────── Misc utilities ─────────
{
    "request": "Go HTTP client with timeout and retry",
    "language": "go", "framework": "golang",
    "code": """package httpx

import (
\t"io"
\t"net/http"
\t"time"
)

var client = &http.Client{Timeout: 10 * time.Second}

func GetWithRetry(url string, attempts int) ([]byte, error) {
\tvar lastErr error
\tfor i := 0; i < attempts; i++ {
\t\tresp, err := client.Get(url)
\t\tif err == nil && resp.StatusCode < 500 {
\t\t\tdefer resp.Body.Close()
\t\t\treturn io.ReadAll(resp.Body)
\t\t}
\t\tif resp != nil {
\t\t\tresp.Body.Close()
\t\t}
\t\tlastErr = err
\t\ttime.Sleep(time.Duration(i+1) * 200 * time.Millisecond)
\t}
\treturn nil, lastErr
}""",
},
{
    "request": "Go WebSocket server with gorilla/websocket",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"log"
\t"net/http"

\t"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
\tCheckOrigin: func(r *http.Request) bool { return true },
}

func wsHandler(w http.ResponseWriter, r *http.Request) {
\tconn, err := upgrader.Upgrade(w, r, nil)
\tif err != nil {
\t\tlog.Println(err)
\t\treturn
\t}
\tdefer conn.Close()

\tfor {
\t\tmt, msg, err := conn.ReadMessage()
\t\tif err != nil {
\t\t\tlog.Println("read:", err)
\t\t\tbreak
\t\t}
\t\tlog.Printf("recv: %s", msg)
\t\tif err := conn.WriteMessage(mt, msg); err != nil {
\t\t\tbreak
\t\t}
\t}
}

func main() {
\thttp.HandleFunc("/ws", wsHandler)
\tlog.Fatal(http.ListenAndServe(":8080", nil))
}""",
},
{
    "request": "Go file upload handler with multipart form",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"io"
\t"net/http"
\t"os"
\t"path/filepath"
)

func uploadHandler(w http.ResponseWriter, r *http.Request) {
\tif err := r.ParseMultipartForm(10 << 20); err != nil { // 10 MB
\t\thttp.Error(w, err.Error(), http.StatusBadRequest)
\t\treturn
\t}
\tfile, header, err := r.FormFile("file")
\tif err != nil {
\t\thttp.Error(w, err.Error(), http.StatusBadRequest)
\t\treturn
\t}
\tdefer file.Close()

\tos.MkdirAll("uploads", 0o755)
\tdst, err := os.Create(filepath.Join("uploads", filepath.Base(header.Filename)))
\tif err != nil {
\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)
\t\treturn
\t}
\tdefer dst.Close()

\tn, err := io.Copy(dst, file)
\tif err != nil {
\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)
\t\treturn
\t}
\tw.Write([]byte("uploaded " + header.Filename + " (" + http.StatusText(http.StatusOK) + ")"))
\t_ = n
}""",
},
{
    "request": "Go gRPC server skeleton with proto",
    "language": "go", "framework": "golang",
    "code": """// proto/greeter.proto
//   syntax = "proto3";
//   service Greeter { rpc Hello(HelloReq) returns (HelloResp); }
//   message HelloReq  { string name = 1; }
//   message HelloResp { string message = 2; }
//
// Generate: protoc --go_out=. --go-grpc_out=. proto/greeter.proto

package main

import (
\t"context"
\t"log"
\t"net"

\t"google.golang.org/grpc"
\tpb "github.com/you/myapp/proto"
)

type server struct{ pb.UnimplementedGreeterServer }

func (s *server) Hello(ctx context.Context, in *pb.HelloReq) (*pb.HelloResp, error) {
\treturn &pb.HelloResp{Message: "hello, " + in.Name}, nil
}

func main() {
\tlis, err := net.Listen("tcp", ":50051")
\tif err != nil {
\t\tlog.Fatal(err)
\t}
\ts := grpc.NewServer()
\tpb.RegisterGreeterServer(s, &server{})
\tlog.Println("grpc listening on :50051")
\tlog.Fatal(s.Serve(lis))
}""",
},
{
    "request": "Go repository pattern with interface for testability",
    "language": "go", "framework": "golang",
    "code": """package store

import (
\t"context"
\t"database/sql"
)

type User struct {
\tID    int
\tName  string
\tEmail string
}

type UserRepo interface {
\tCreate(ctx context.Context, u *User) error
\tGetByID(ctx context.Context, id int) (*User, error)
}

type pgUserRepo struct{ db *sql.DB }

func NewUserRepo(db *sql.DB) UserRepo { return &pgUserRepo{db: db} }

func (r *pgUserRepo) Create(ctx context.Context, u *User) error {
\treturn r.db.QueryRowContext(ctx,
\t\t`INSERT INTO users(name,email) VALUES($1,$2) RETURNING id`,
\t\tu.Name, u.Email,
\t).Scan(&u.ID)
}

func (r *pgUserRepo) GetByID(ctx context.Context, id int) (*User, error) {
\tu := &User{}
\terr := r.db.QueryRowContext(ctx,
\t\t`SELECT id,name,email FROM users WHERE id=$1`, id,
\t).Scan(&u.ID, &u.Name, &u.Email)
\tif err == sql.ErrNoRows {
\t\treturn nil, nil
\t}
\treturn u, err
}""",
},
{
    "request": "Dockerfile multi-stage build for Go binary",
    "language": "dockerfile", "framework": "golang",
    "code": """# build stage
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/server ./cmd/server

# runtime stage
FROM gcr.io/distroless/static-debian12
COPY --from=build /out/server /server
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/server"]""",
},
{
    "request": "Go CLI with cobra commands and flags",
    "language": "go", "framework": "golang",
    "code": """package main

import (
\t"fmt"
\t"os"

\t"github.com/spf13/cobra"
)

var (
\tverbose bool
\tname    string
)

var rootCmd = &cobra.Command{
\tUse:   "mytool",
\tShort: "mytool does things",
}

var greetCmd = &cobra.Command{
\tUse:   "greet",
\tShort: "say hello",
\tRun: func(cmd *cobra.Command, args []string) {
\t\tif verbose {
\t\t\tfmt.Println("verbose mode on")
\t\t}
\t\tfmt.Println("hello,", name)
\t},
}

func main() {
\trootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
\tgreetCmd.Flags().StringVarP(&name, "name", "n", "world", "name to greet")
\trootCmd.AddCommand(greetCmd)
\tif err := rootCmd.Execute(); err != nil {
\t\tos.Exit(1)
\t}
}""",
},
]
