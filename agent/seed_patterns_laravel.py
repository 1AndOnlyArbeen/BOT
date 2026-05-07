"""Laravel / PHP reference patterns. Routes, controllers, Eloquent, migrations,
auth (Sanctum), validation, queues, mail, testing."""
from __future__ import annotations


LARAVEL_SEED: list[dict] = [
{
    "request": "create a new Laravel project from scratch",
    "language": "bash", "framework": "laravel",
    "code": """composer create-project laravel/laravel my-app
cd my-app
cp .env.example .env
php artisan key:generate
php artisan serve         # http://127.0.0.1:8000

# common adds:
composer require laravel/sanctum
php artisan vendor:publish --provider="Laravel\\Sanctum\\SanctumServiceProvider\"
php artisan migrate""",
},
{
    "request": "Laravel project structure overview",
    "language": "text", "framework": "laravel",
    "code": """app/
  Http/
    Controllers/        # request handlers
    Middleware/
    Requests/           # form-request validation
    Resources/          # API JSON resources
  Models/               # Eloquent models
  Jobs/                 # queueable units
  Events/  Listeners/   # event-driven flow
  Mail/                 # mailables
  Providers/            # service providers
bootstrap/
config/                 # one file per concern (auth, mail, queue, …)
database/
  migrations/  factories/  seeders/
routes/
  web.php  api.php  console.php
resources/views/        # Blade templates
tests/                  # Pest / PHPUnit
.env                    # environment""",
},
{
    "request": "Laravel route definitions web and API",
    "language": "php", "framework": "laravel",
    "code": """// routes/web.php
use Illuminate\\Support\\Facades\\Route;
use App\\Http\\Controllers\\PostController;

Route::get('/',         fn () => view('welcome'));
Route::resource('posts', PostController::class);   // index/create/store/show/edit/update/destroy

// routes/api.php
use Illuminate\\Support\\Facades\\Route;
use App\\Http\\Controllers\\Api\\UserController;

Route::middleware('auth:sanctum')->group(function () {
    Route::get('/me', fn (Request $r) => $r->user());
    Route::apiResource('users', UserController::class);
});""",
},
{
    "request": "Laravel resource controller with all CRUD methods",
    "language": "php", "framework": "laravel",
    "code": """<?php

namespace App\\Http\\Controllers;

use App\\Http\\Requests\\StorePostRequest;
use App\\Http\\Requests\\UpdatePostRequest;
use App\\Models\\Post;
use Illuminate\\Http\\Request;

class PostController extends Controller
{
    public function index(Request $request)
    {
        $posts = Post::latest()->paginate(15);
        return view('posts.index', compact('posts'));
    }

    public function store(StorePostRequest $request)
    {
        $post = $request->user()->posts()->create($request->validated());
        return redirect()->route('posts.show', $post);
    }

    public function show(Post $post)
    {
        return view('posts.show', compact('post'));
    }

    public function update(UpdatePostRequest $request, Post $post)
    {
        $this->authorize('update', $post);
        $post->update($request->validated());
        return redirect()->route('posts.show', $post);
    }

    public function destroy(Post $post)
    {
        $this->authorize('delete', $post);
        $post->delete();
        return redirect()->route('posts.index');
    }
}""",
},
{
    "request": "Laravel Eloquent model with relationships and scopes",
    "language": "php", "framework": "laravel",
    "code": """<?php

namespace App\\Models;

use Illuminate\\Database\\Eloquent\\Factories\\HasFactory;
use Illuminate\\Database\\Eloquent\\Model;
use Illuminate\\Database\\Eloquent\\Relations\\BelongsTo;
use Illuminate\\Database\\Eloquent\\Relations\\HasMany;

class Post extends Model
{
    use HasFactory;

    protected $fillable = ['title', 'body', 'status'];

    protected $casts = [
        'published_at' => 'datetime',
        'metadata'     => 'array',
    ];

    public function author(): BelongsTo {
        return $this->belongsTo(User::class, 'user_id');
    }

    public function comments(): HasMany {
        return $this->hasMany(Comment::class);
    }

    /** Scope: only published posts. */
    public function scopePublished($query)
    {
        return $query->where('status', 'published')
                     ->whereNotNull('published_at');
    }
}

// usage: Post::published()->latest()->take(5)->get();""",
},
{
    "request": "Laravel migration creating posts table",
    "language": "php", "framework": "laravel",
    "code": """<?php

use Illuminate\\Database\\Migrations\\Migration;
use Illuminate\\Database\\Schema\\Blueprint;
use Illuminate\\Support\\Facades\\Schema;

return new class extends Migration {
    public function up(): void
    {
        Schema::create('posts', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->string('title');
            $table->longText('body');
            $table->enum('status', ['draft', 'published'])->default('draft');
            $table->timestamp('published_at')->nullable();
            $table->json('metadata')->nullable();
            $table->timestamps();
            $table->index(['status', 'published_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('posts');
    }
};""",
},
{
    "request": "Laravel model factory and seeder",
    "language": "php", "framework": "laravel",
    "code": """<?php
// database/factories/PostFactory.php

namespace Database\\Factories;

use App\\Models\\Post;
use App\\Models\\User;
use Illuminate\\Database\\Eloquent\\Factories\\Factory;

class PostFactory extends Factory
{
    protected $model = Post::class;

    public function definition(): array
    {
        return [
            'user_id'      => User::factory(),
            'title'        => fake()->sentence(),
            'body'         => fake()->paragraphs(5, true),
            'status'       => fake()->randomElement(['draft', 'published']),
            'published_at' => fake()->optional()->dateTimeBetween('-1 year'),
        ];
    }

    public function published(): self
    {
        return $this->state(fn () => [
            'status' => 'published',
            'published_at' => now(),
        ]);
    }
}

// database/seeders/DatabaseSeeder.php
public function run(): void
{
    \\App\\Models\\User::factory()->has(Post::factory()->count(5)->published())->count(10)->create();
}""",
},
{
    "request": "Laravel form request validation",
    "language": "php", "framework": "laravel",
    "code": """<?php
// app/Http/Requests/StorePostRequest.php

namespace App\\Http\\Requests;

use Illuminate\\Foundation\\Http\\FormRequest;

class StorePostRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user() !== null;
    }

    public function rules(): array
    {
        return [
            'title'  => ['required', 'string', 'min:3', 'max:200'],
            'body'   => ['required', 'string', 'min:10'],
            'status' => ['nullable', 'in:draft,published'],
            'tags'   => ['array', 'max:5'],
            'tags.*' => ['string', 'max:30'],
        ];
    }

    public function messages(): array
    {
        return [
            'title.required' => 'Posts need a title.',
        ];
    }
}""",
},
{
    "request": "Laravel Sanctum token authentication",
    "language": "php", "framework": "laravel",
    "code": """<?php
// install:
//   composer require laravel/sanctum
//   php artisan vendor:publish --provider="Laravel\\Sanctum\\SanctumServiceProvider"
//   php artisan migrate

// app/Models/User.php
use Laravel\\Sanctum\\HasApiTokens;
class User extends Authenticatable {
    use HasApiTokens, HasFactory, Notifiable;
}

// routes/api.php
Route::post('/login', function (Request $r) {
    $r->validate(['email' => 'required|email', 'password' => 'required']);
    if (!Auth::attempt($r->only('email', 'password'))) {
        return response()->json(['message' => 'invalid'], 401);
    }
    $token = $r->user()->createToken('api')->plainTextToken;
    return ['token' => $token];
});

Route::middleware('auth:sanctum')->group(function () {
    Route::get('/me', fn (Request $r) => $r->user());
    Route::post('/logout', fn (Request $r) => $r->user()->currentAccessToken()->delete());
});""",
},
{
    "request": "Laravel API resource for JSON serialization",
    "language": "php", "framework": "laravel",
    "code": """<?php
// app/Http/Resources/PostResource.php

namespace App\\Http\\Resources;

use Illuminate\\Http\\Resources\\Json\\JsonResource;

class PostResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id'           => $this->id,
            'title'        => $this->title,
            'excerpt'      => str($this->body)->limit(200),
            'status'       => $this->status,
            'published_at' => $this->published_at?->toIso8601String(),
            'author'       => UserResource::make($this->whenLoaded('author')),
            'comments_count' => $this->whenCounted('comments'),
        ];
    }
}

// usage in controller:
//   return PostResource::collection(Post::latest()->paginate(15));
//   return PostResource::make($post->load('author')->loadCount('comments'));""",
},
{
    "request": "Laravel queueable job with retry",
    "language": "php", "framework": "laravel",
    "code": """<?php
// php artisan make:job SendWelcomeEmail

namespace App\\Jobs;

use App\\Mail\\WelcomeMail;
use App\\Models\\User;
use Illuminate\\Bus\\Queueable;
use Illuminate\\Contracts\\Queue\\ShouldQueue;
use Illuminate\\Foundation\\Bus\\Dispatchable;
use Illuminate\\Queue\\InteractsWithQueue;
use Illuminate\\Queue\\SerializesModels;
use Illuminate\\Support\\Facades\\Mail;

class SendWelcomeEmail implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 3;
    public int $backoff = 30;       // seconds between retries
    public int $timeout = 60;

    public function __construct(public User $user) {}

    public function handle(): void
    {
        Mail::to($this->user->email)->send(new WelcomeMail($this->user));
    }

    public function failed(\\Throwable $e): void
    {
        logger()->error('welcome email failed', ['user' => $this->user->id, 'err' => $e->getMessage()]);
    }
}

// dispatch: SendWelcomeEmail::dispatch($user)->delay(now()->addMinutes(5));""",
},
{
    "request": "Laravel mailable class with markdown",
    "language": "php", "framework": "laravel",
    "code": """<?php
// php artisan make:mail WelcomeMail --markdown=emails.welcome

namespace App\\Mail;

use App\\Models\\User;
use Illuminate\\Bus\\Queueable;
use Illuminate\\Mail\\Mailable;
use Illuminate\\Mail\\Mailables\\Content;
use Illuminate\\Mail\\Mailables\\Envelope;
use Illuminate\\Queue\\SerializesModels;

class WelcomeMail extends Mailable
{
    use Queueable, SerializesModels;

    public function __construct(public User $user) {}

    public function envelope(): Envelope
    {
        return new Envelope(subject: "Welcome, {$this->user->name}");
    }

    public function content(): Content
    {
        return new Content(markdown: 'emails.welcome', with: ['user' => $this->user]);
    }
}

// resources/views/emails/welcome.blade.php
// @component('mail::message')
// # Hi {{ $user->name }}
// Thanks for joining!
// @component('mail::button', ['url' => route('home')]) Visit @endcomponent
// @endcomponent""",
},
{
    "request": "Laravel events and listeners pattern",
    "language": "php", "framework": "laravel",
    "code": """<?php
// php artisan make:event UserRegistered
namespace App\\Events;

use App\\Models\\User;
use Illuminate\\Foundation\\Events\\Dispatchable;
use Illuminate\\Queue\\SerializesModels;

class UserRegistered
{
    use Dispatchable, SerializesModels;
    public function __construct(public User $user) {}
}

// php artisan make:listener SendWelcomeNotification --event=UserRegistered
namespace App\\Listeners;

use App\\Events\\UserRegistered;
use App\\Jobs\\SendWelcomeEmail;
use Illuminate\\Contracts\\Queue\\ShouldQueue;

class SendWelcomeNotification implements ShouldQueue
{
    public function handle(UserRegistered $e): void
    {
        SendWelcomeEmail::dispatch($e->user);
    }
}

// app/Providers/EventServiceProvider.php
// protected $listen = [
//     UserRegistered::class => [SendWelcomeNotification::class],
// ];

// fire: event(new UserRegistered($user));""",
},
{
    "request": "Laravel cache with tags and remember",
    "language": "php", "framework": "laravel",
    "code": """<?php

use Illuminate\\Support\\Facades\\Cache;

// simple TTL cache
$users = Cache::remember('users.top', now()->addMinutes(10), function () {
    return \\App\\Models\\User::orderByDesc('points')->take(50)->get();
});

// tag-based invalidation (only redis/memcached drivers support this)
Cache::tags(['users'])->put("user.{$id}", $user, 600);
$user = Cache::tags(['users'])->get("user.{$id}");

// invalidate everything tagged
Cache::tags(['users'])->flush();

// rate-limit pattern
$key = 'login.' . $request->ip();
if (Cache::increment($key) > 5) {
    abort(429, 'too many attempts');
}
Cache::put($key, Cache::get($key), now()->addMinute());""",
},
{
    "request": "Laravel file upload with validation and storage",
    "language": "php", "framework": "laravel",
    "code": """<?php

public function store(Request $request)
{
    $request->validate([
        'avatar' => ['required', 'image', 'max:2048'],   // KB
    ]);

    // disk config in config/filesystems.php (s3, public, local…)
    $path = $request->file('avatar')->store('avatars', 'public');

    auth()->user()->update(['avatar_path' => $path]);

    return back()->with('status', 'avatar updated');
}

// blade form:
// <form method="POST" action="/profile/avatar" enctype="multipart/form-data">
//   @csrf
//   <input type="file" name="avatar">
//   <button>upload</button>
// </form>

// link back:
// <img src="{{ Storage::url($user->avatar_path) }}">""",
},
{
    "request": "Laravel artisan command to send daily report",
    "language": "php", "framework": "laravel",
    "code": """<?php
// php artisan make:command SendDailyReport

namespace App\\Console\\Commands;

use App\\Mail\\DailyReport;
use Illuminate\\Console\\Command;
use Illuminate\\Support\\Facades\\Mail;

class SendDailyReport extends Command
{
    protected $signature = 'report:daily {--dry}';
    protected $description = 'Email yesterday\\'s metrics summary';

    public function handle(): int
    {
        $report = ['signups' => 42, 'revenue' => 1280.50];

        if ($this->option('dry')) {
            $this->info(json_encode($report, JSON_PRETTY_PRINT));
            return self::SUCCESS;
        }

        Mail::to('admin@example.com')->send(new DailyReport($report));
        $this->info('sent');
        return self::SUCCESS;
    }
}

// app/Console/Kernel.php — schedule it:
// $schedule->command('report:daily')->dailyAt('07:00');""",
},
{
    "request": "Laravel feature test with Pest",
    "language": "php", "framework": "laravel",
    "code": """<?php

use App\\Models\\User;
use App\\Models\\Post;
use function Pest\\Laravel\\actingAs;

it('lets a user create a post', function () {
    $user = User::factory()->create();

    actingAs($user)
        ->post('/posts', [
            'title' => 'My first post',
            'body'  => 'A long enough body for validation to pass.',
        ])
        ->assertRedirect();

    expect(Post::where('user_id', $user->id)->count())->toBe(1);
});

it('rejects empty title', function () {
    actingAs(User::factory()->create())
        ->post('/posts', ['body' => 'something here'])
        ->assertSessionHasErrors('title');
});""",
},
{
    "request": "Laravel pagination with custom view",
    "language": "php", "framework": "laravel",
    "code": """<?php
// Controller
public function index(Request $r)
{
    $posts = Post::published()
        ->when($r->q, fn ($q, $term) => $q->where('title', 'like', "%{$term}%"))
        ->latest()
        ->paginate(20)
        ->withQueryString();   // preserve ?q= in pagination links

    return view('posts.index', compact('posts'));
}

// Blade: posts.index.blade.php
// @foreach ($posts as $post) <h2>{{ $post->title }}</h2> @endforeach
// {{ $posts->links() }}      {{-- default tailwind-styled links --}}
// {{ $posts->onEachSide(2)->links() }}  {{-- show ±2 around current page --}}""",
},
]
