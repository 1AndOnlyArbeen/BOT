"""C# / .NET reference patterns. Console + ASP.NET Core (minimal API + MVC),
Entity Framework Core, DI, JWT auth, background services, xUnit tests."""
from __future__ import annotations


DOTNET_SEED: list[dict] = [
{
    "request": "create a new .NET 8 project from scratch",
    "language": "bash", "framework": "dotnet",
    "code": """dotnet --version          # confirm .NET 8 installed
dotnet new webapi -n MyApi --use-minimal-apis --no-openapi=false
cd MyApi
dotnet run                # https://localhost:5001""",
},
{
    "request": "C# .csproj nullable + implicit usings",
    "language": "xml", "framework": "dotnet",
    "code": """<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>MyApi</RootNamespace>
    <InvariantGlobalization>true</InvariantGlobalization>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Design"     Version="8.0.0" />
    <PackageReference Include="Swashbuckle.AspNetCore"                   Version="6.5.0" />
  </ItemGroup>
</Project>""",
},
{
    "request": "ASP.NET Core minimal API with Program.cs",
    "language": "csharp", "framework": "dotnet",
    "code": """var builder = WebApplication.CreateBuilder(args);
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

app.UseSwagger();
app.UseSwaggerUI();

app.MapGet("/", () => "hello, world");

app.MapGet("/users/{id:int}", (int id) => new { id, name = $"User {id}" });

app.MapPost("/users", (CreateUser req) => Results.Created($"/users/1", new { id = 1, req.Name }));

app.Run();

record CreateUser(string Name, string Email);""",
},
{
    "request": "ASP.NET Core MVC controller with attribute routing",
    "language": "csharp", "framework": "dotnet",
    "code": """using Microsoft.AspNetCore.Mvc;

namespace MyApi.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    [HttpGet]
    public IActionResult List() =>
        Ok(new[] { new { id = 1, name = "Ada" } });

    [HttpGet("{id:int}")]
    public IActionResult GetOne(int id) =>
        id > 0 ? Ok(new { id, name = $"User {id}" })
               : NotFound();

    [HttpPost]
    public IActionResult Create([FromBody] CreateUserDto dto) =>
        CreatedAtAction(nameof(GetOne), new { id = 1 }, dto);
}

public record CreateUserDto(string Name, string Email);""",
},
{
    "request": "Entity Framework Core DbContext with migrations",
    "language": "csharp", "framework": "dotnet",
    "code": """// Models/User.cs
public class User
{
    public int Id { get; set; }
    public required string Name  { get; set; }
    public required string Email { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

// Data/AppDbContext.cs
using Microsoft.EntityFrameworkCore;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> opts) : base(opts) { }
    public DbSet<User> Users => Set<User>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        b.Entity<User>().HasIndex(u => u.Email).IsUnique();
    }
}

// Program.cs registration
// builder.Services.AddDbContext<AppDbContext>(o =>
//     o.UseSqlServer(builder.Configuration.GetConnectionString("Default")));

// CLI:
//   dotnet ef migrations add InitialCreate
//   dotnet ef database update""",
},
{
    "request": "C# dependency injection with constructor injection",
    "language": "csharp", "framework": "dotnet",
    "code": """// IUserService + UserService
public interface IUserService { Task<User?> GetAsync(int id); }

public class UserService : IUserService
{
    private readonly AppDbContext _db;
    public UserService(AppDbContext db) => _db = db;

    public Task<User?> GetAsync(int id) => _db.Users.FindAsync(id).AsTask();
}

// Program.cs
// builder.Services.AddScoped<IUserService, UserService>();

// Controller
[ApiController]
[Route("api/[controller]")]
public class UsersController : ControllerBase
{
    private readonly IUserService _users;
    public UsersController(IUserService users) => _users = users;

    [HttpGet("{id:int}")]
    public async Task<IActionResult> Get(int id) =>
        (await _users.GetAsync(id)) is { } u ? Ok(u) : NotFound();
}""",
},
{
    "request": "ASP.NET Core JWT authentication setup",
    "language": "csharp", "framework": "dotnet",
    "code": """// Program.cs
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using System.Text;

var builder = WebApplication.CreateBuilder(args);
var key = Encoding.UTF8.GetBytes(builder.Configuration["Jwt:Key"]!);

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(o => o.TokenValidationParameters = new TokenValidationParameters {
        ValidateIssuer = true,
        ValidateAudience = true,
        ValidateLifetime = true,
        ValidateIssuerSigningKey = true,
        ValidIssuer = builder.Configuration["Jwt:Issuer"],
        ValidAudience = builder.Configuration["Jwt:Audience"],
        IssuerSigningKey = new SymmetricSecurityKey(key),
    });

builder.Services.AddAuthorization();

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();

app.MapGet("/me", (ClaimsPrincipal user) => new { name = user.Identity?.Name })
   .RequireAuthorization();

app.Run();""",
},
{
    "request": "C# issue JWT token with claims",
    "language": "csharp", "framework": "dotnet",
    "code": """using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;

public static class JwtIssuer
{
    public static string Issue(int userId, string email, string secret, string issuer, string audience)
    {
        var claims = new[] {
            new Claim(JwtRegisteredClaimNames.Sub, userId.ToString()),
            new Claim(JwtRegisteredClaimNames.Email, email),
            new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
        };
        var key   = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(secret));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);
        var token = new JwtSecurityToken(
            issuer, audience, claims,
            expires: DateTime.UtcNow.AddHours(8),
            signingCredentials: creds);
        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}""",
},
{
    "request": "ASP.NET Core middleware to log requests",
    "language": "csharp", "framework": "dotnet",
    "code": """public class RequestLoggingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<RequestLoggingMiddleware> _log;

    public RequestLoggingMiddleware(RequestDelegate next, ILogger<RequestLoggingMiddleware> log)
    {
        _next = next;
        _log  = log;
    }

    public async Task InvokeAsync(HttpContext ctx)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        await _next(ctx);
        _log.LogInformation("{Method} {Path} → {Status} in {Ms}ms",
            ctx.Request.Method, ctx.Request.Path, ctx.Response.StatusCode, sw.ElapsedMilliseconds);
    }
}

// Program.cs
// app.UseMiddleware<RequestLoggingMiddleware>();""",
},
{
    "request": "C# BackgroundService for hosted recurring task",
    "language": "csharp", "framework": "dotnet",
    "code": """using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

public class CleanupWorker : BackgroundService
{
    private readonly ILogger<CleanupWorker> _log;
    public CleanupWorker(ILogger<CleanupWorker> log) => _log = log;

    protected override async Task ExecuteAsync(CancellationToken stop)
    {
        while (!stop.IsCancellationRequested)
        {
            try
            {
                _log.LogInformation("running cleanup");
                // do work
            }
            catch (Exception ex)
            {
                _log.LogError(ex, "cleanup failed");
            }
            await Task.Delay(TimeSpan.FromMinutes(5), stop);
        }
    }
}

// Program.cs
// builder.Services.AddHostedService<CleanupWorker>();""",
},
{
    "request": "C# strongly-typed configuration with IOptions",
    "language": "csharp", "framework": "dotnet",
    "code": """// Settings.cs
public class JwtSettings
{
    public required string Key { get; set; }
    public required string Issuer { get; set; }
    public required string Audience { get; set; }
    public int LifetimeMinutes { get; set; } = 60;
}

// Program.cs
// builder.Services.Configure<JwtSettings>(builder.Configuration.GetSection("Jwt"));

// Consumer:
public class TokenService
{
    private readonly JwtSettings _opt;
    public TokenService(IOptions<JwtSettings> opt) => _opt = opt.Value;
}

// appsettings.json
// "Jwt": { "Key": "…", "Issuer": "myapp", "Audience": "myapp", "LifetimeMinutes": 60 }""",
},
{
    "request": "C# HttpClient with named client and IHttpClientFactory",
    "language": "csharp", "framework": "dotnet",
    "code": """// Program.cs
// builder.Services.AddHttpClient("github", c => {
//     c.BaseAddress = new Uri("https://api.github.com/");
//     c.DefaultRequestHeaders.Add("User-Agent", "myapp");
// });

public class GitHubService
{
    private readonly HttpClient _http;
    public GitHubService(IHttpClientFactory f) => _http = f.CreateClient("github");

    public async Task<string> GetUserAsync(string login)
    {
        var resp = await _http.GetAsync($"users/{login}");
        resp.EnsureSuccessStatusCode();
        return await resp.Content.ReadAsStringAsync();
    }
}""",
},
{
    "request": "C# async LINQ over EF Core",
    "language": "csharp", "framework": "dotnet",
    "code": """using Microsoft.EntityFrameworkCore;

public class UserRepo
{
    private readonly AppDbContext _db;
    public UserRepo(AppDbContext db) => _db = db;

    public Task<List<User>> RecentAsync(int count) =>
        _db.Users.AsNoTracking()
                 .OrderByDescending(u => u.CreatedAt)
                 .Take(count)
                 .ToListAsync();

    public Task<User?> ByEmailAsync(string email) =>
        _db.Users.FirstOrDefaultAsync(u => u.Email == email);

    public async Task<bool> DeleteAsync(int id)
    {
        var u = await _db.Users.FindAsync(id);
        if (u == null) return false;
        _db.Users.Remove(u);
        await _db.SaveChangesAsync();
        return true;
    }
}""",
},
{
    "request": "C# records and pattern matching",
    "language": "csharp", "framework": "dotnet",
    "code": """// Records — immutable value types with structural equality.
public record Money(decimal Amount, string Currency);
public record Address(string Street, string City);

// 'with' expressions for non-destructive mutation
var a = new Money(100, "USD");
var b = a with { Amount = 200 };

// Pattern matching:
public static string Classify(object o) => o switch
{
    int n when n > 0  => "positive int",
    int n when n < 0  => "negative int",
    string { Length: > 0 } s => $"non-empty string of length {s.Length}",
    Money { Amount: > 1000 } m => $"big money: {m.Currency}",
    null              => "null",
    _                 => "other",
};""",
},
{
    "request": "C# xUnit test with Theory and InlineData",
    "language": "csharp", "framework": "dotnet",
    "code": """using Xunit;
using FluentAssertions;

public class CalculatorTests
{
    [Fact]
    public void Add_TwoPositives_Sum()
    {
        var c = new Calculator();
        c.Add(2, 3).Should().Be(5);
    }

    [Theory]
    [InlineData(0, 0, 0)]
    [InlineData(1, 1, 2)]
    [InlineData(-1, 1, 0)]
    public void Add_Cases(int a, int b, int expected)
    {
        new Calculator().Add(a, b).Should().Be(expected);
    }
}

public class Calculator { public int Add(int a, int b) => a + b; }""",
},
{
    "request": "C# integration test with WebApplicationFactory",
    "language": "csharp", "framework": "dotnet",
    "code": """using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

public class HealthEndpointTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;
    public HealthEndpointTests(WebApplicationFactory<Program> f) => _client = f.CreateClient();

    [Fact]
    public async Task Health_ReturnsOk()
    {
        var resp = await _client.GetAsync("/health");
        Assert.Equal(System.Net.HttpStatusCode.OK, resp.StatusCode);
    }
}""",
},
{
    "request": "C# global exception handler middleware",
    "language": "csharp", "framework": "dotnet",
    "code": """public class ExceptionHandlerMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<ExceptionHandlerMiddleware> _log;

    public ExceptionHandlerMiddleware(RequestDelegate next, ILogger<ExceptionHandlerMiddleware> log)
    { _next = next; _log = log; }

    public async Task InvokeAsync(HttpContext ctx)
    {
        try
        {
            await _next(ctx);
        }
        catch (KeyNotFoundException) { ctx.Response.StatusCode = 404; }
        catch (UnauthorizedAccessException) { ctx.Response.StatusCode = 401; }
        catch (Exception ex)
        {
            _log.LogError(ex, "unhandled");
            ctx.Response.StatusCode = 500;
            await ctx.Response.WriteAsJsonAsync(new { error = "internal error" });
        }
    }
}""",
},
{
    "request": "ASP.NET Core CORS configuration",
    "language": "csharp", "framework": "dotnet",
    "code": """// Program.cs
builder.Services.AddCors(o => o.AddPolicy("frontend", p => p
    .WithOrigins("https://my.app", "http://localhost:5173")
    .AllowAnyHeader()
    .AllowAnyMethod()
    .AllowCredentials()));

var app = builder.Build();
app.UseCors("frontend");

// per-endpoint:
// app.MapGet("/public", () => "ok").RequireCors("frontend");""",
},
{
    "request": "ASP.NET Core SignalR hub + client",
    "language": "csharp", "framework": "dotnet",
    "code": """// Hubs/ChatHub.cs
using Microsoft.AspNetCore.SignalR;

public class ChatHub : Hub
{
    public Task Send(string user, string message) =>
        Clients.All.SendAsync("ReceiveMessage", user, message);
}

// Program.cs
// builder.Services.AddSignalR();
// app.MapHub<ChatHub>("/hubs/chat");

// JS client
/*
const conn = new signalR.HubConnectionBuilder().withUrl("/hubs/chat").build();
conn.on("ReceiveMessage", (u, m) => console.log(u, m));
await conn.start();
await conn.invoke("Send", "Ada", "hi");
*/""",
},
{
    "request": "C# file I/O async read and write",
    "language": "csharp", "framework": "dotnet",
    "code": """using System.Text.Json;

public static class FileOps
{
    public static async Task<List<T>> ReadJsonAsync<T>(string path)
    {
        await using var stream = File.OpenRead(path);
        var data = await JsonSerializer.DeserializeAsync<List<T>>(stream);
        return data ?? new();
    }

    public static async Task WriteJsonAsync<T>(string path, IEnumerable<T> items)
    {
        await using var stream = File.Create(path);
        await JsonSerializer.SerializeAsync(stream, items, new JsonSerializerOptions { WriteIndented = true });
    }

    public static async Task AppendLineAsync(string path, string line) =>
        await File.AppendAllTextAsync(path, line + Environment.NewLine);
}""",
},
{
    "request": "C# CancellationToken propagation through service chain",
    "language": "csharp", "framework": "dotnet",
    "code": """public class ReportService
{
    private readonly HttpClient _http;
    public ReportService(HttpClient http) => _http = http;

    public async Task<string> BuildAsync(int id, CancellationToken ct = default)
    {
        var data = await _http.GetStringAsync($"/data/{id}", ct);
        await Task.Delay(500, ct);
        return $"Report({id}): {data.Length} chars";
    }
}

// Caller — token will cancel the whole chain when the request is aborted.
public async Task<IResult> GetReport(int id, CancellationToken ct, ReportService svc)
    => Results.Ok(await svc.BuildAsync(id, ct));""",
},
{
    "request": "Dockerfile for ASP.NET Core 8 multi-stage",
    "language": "dockerfile", "framework": "dotnet",
    "code": """# build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY *.csproj ./
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app /p:UseAppHost=false

# runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /app .
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
ENTRYPOINT ["dotnet", "MyApi.dll"]""",
},
]
