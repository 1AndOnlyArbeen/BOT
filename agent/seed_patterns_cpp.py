"""Modern C++ (C++17/20) reference patterns. CMake, RAII, smart pointers,
STL, threading, file I/O, JSON, HTTP, testing."""
from __future__ import annotations


CPP_SEED: list[dict] = [
{
    "request": "create a new C++ project with CMake",
    "language": "bash", "framework": "cpp",
    "code": """mkdir my-app && cd my-app
mkdir -p src include build
# CMakeLists.txt below
cd build && cmake .. && cmake --build . && ./my-app""",
},
{
    "request": "minimal CMakeLists.txt for C++20 project",
    "language": "cmake", "framework": "cpp",
    "code": """cmake_minimum_required(VERSION 3.20)
project(my-app LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

add_compile_options(-Wall -Wextra -Wpedantic)

add_executable(my-app
    src/main.cpp
    src/server.cpp
)
target_include_directories(my-app PRIVATE include)

# external libs:
# find_package(Threads REQUIRED)
# target_link_libraries(my-app PRIVATE Threads::Threads)""",
},
{
    "request": "C++ smart pointers RAII pattern",
    "language": "cpp", "framework": "cpp",
    "code": """#include <memory>
#include <iostream>

struct Connection {
    explicit Connection(const std::string& host) { std::cout << "open " << host << "\\n"; }
    ~Connection()                                 { std::cout << "close\\n"; }
    void send(const std::string& msg)             { std::cout << "send: " << msg << "\\n"; }
};

void use_unique() {
    auto c = std::make_unique<Connection>("localhost"); // exclusive ownership
    c->send("hi");
    // destructor runs automatically when c goes out of scope
}

void use_shared() {
    auto c = std::make_shared<Connection>("localhost"); // ref-counted
    auto c2 = c;                                         // both own it
    c2->send("hi");
}                                                        // last copy destructed → close""",
},
{
    "request": "C++ move semantics and rule of zero",
    "language": "cpp", "framework": "cpp",
    "code": """#include <vector>
#include <string>
#include <utility>

// Rule of zero: hold resources via RAII types (vector, string, unique_ptr).
// You then DON'T need to write destructor / copy / move — compiler does it.
class Document {
public:
    Document(std::string title, std::vector<std::string> lines)
        : title_(std::move(title)), lines_(std::move(lines)) {}

    const std::string& title() const noexcept { return title_; }
    const std::vector<std::string>& lines() const noexcept { return lines_; }

private:
    std::string title_;
    std::vector<std::string> lines_;
};

// usage:
Document make() {
    return Document("Report", {"line one", "line two"}); // moved out, no copies
}""",
},
{
    "request": "C++ STL algorithms with lambda",
    "language": "cpp", "framework": "cpp",
    "code": """#include <algorithm>
#include <vector>
#include <numeric>
#include <iostream>

int main() {
    std::vector<int> v{5, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5};

    // sort + dedup
    std::sort(v.begin(), v.end());
    v.erase(std::unique(v.begin(), v.end()), v.end());

    // count, find, transform
    auto evens = std::count_if(v.begin(), v.end(), [](int n) { return n % 2 == 0; });
    auto big   = std::find_if(v.begin(), v.end(), [](int n) { return n > 5; });
    int  sum   = std::accumulate(v.begin(), v.end(), 0);

    std::vector<int> sq;
    sq.reserve(v.size());
    std::transform(v.begin(), v.end(), std::back_inserter(sq), [](int n) { return n * n; });

    std::cout << "evens=" << evens << " sum=" << sum << "\\n";
}""",
},
{
    "request": "C++ std::thread with mutex and condition_variable",
    "language": "cpp", "framework": "cpp",
    "code": """#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <iostream>

class BoundedQueue {
public:
    explicit BoundedQueue(size_t cap) : cap_(cap) {}

    void push(int x) {
        std::unique_lock lock(mu_);
        not_full_.wait(lock, [&]{ return q_.size() < cap_; });
        q_.push(x);
        not_empty_.notify_one();
    }

    int pop() {
        std::unique_lock lock(mu_);
        not_empty_.wait(lock, [&]{ return !q_.empty(); });
        int v = q_.front(); q_.pop();
        not_full_.notify_one();
        return v;
    }

private:
    size_t cap_;
    std::queue<int> q_;
    std::mutex mu_;
    std::condition_variable not_full_, not_empty_;
};

int main() {
    BoundedQueue q(2);
    std::thread prod([&]{ for (int i=1;i<=5;++i) q.push(i); });
    std::thread cons([&]{ for (int i=0;i<5;++i)  std::cout << q.pop() << "\\n"; });
    prod.join(); cons.join();
}""",
},
{
    "request": "C++ std::async future pattern",
    "language": "cpp", "framework": "cpp",
    "code": """#include <future>
#include <vector>
#include <numeric>
#include <iostream>

long long sum_range(const std::vector<int>& v, size_t lo, size_t hi) {
    return std::accumulate(v.begin()+lo, v.begin()+hi, 0LL);
}

int main() {
    std::vector<int> v(1'000'000, 1);
    size_t mid = v.size() / 2;

    auto f1 = std::async(std::launch::async, sum_range, std::cref(v), 0, mid);
    auto f2 = std::async(std::launch::async, sum_range, std::cref(v), mid, v.size());

    std::cout << "total = " << (f1.get() + f2.get()) << "\\n";
}""",
},
{
    "request": "C++ filesystem read directory and file",
    "language": "cpp", "framework": "cpp",
    "code": """#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>

namespace fs = std::filesystem;

std::string read_text(const fs::path& p) {
    std::ifstream f(p);
    std::stringstream ss; ss << f.rdbuf();
    return ss.str();
}

void list_files(const fs::path& dir) {
    if (!fs::exists(dir) || !fs::is_directory(dir)) return;
    for (const auto& entry : fs::recursive_directory_iterator(dir)) {
        if (entry.is_regular_file() && entry.path().extension() == ".cpp") {
            std::cout << entry.path() << " (" << entry.file_size() << " bytes)\\n";
        }
    }
}""",
},
{
    "request": "C++ JSON with nlohmann/json",
    "language": "cpp", "framework": "cpp",
    "code": """// CMake: find_package(nlohmann_json 3.11.0 REQUIRED)
//        target_link_libraries(my-app PRIVATE nlohmann_json::nlohmann_json)

#include <nlohmann/json.hpp>
#include <iostream>
#include <fstream>

using json = nlohmann::json;

struct User {
    int id;
    std::string name;
    std::string email;
};

void to_json(json& j, const User& u) { j = {{"id", u.id}, {"name", u.name}, {"email", u.email}}; }
void from_json(const json& j, User& u) {
    j.at("id").get_to(u.id);
    j.at("name").get_to(u.name);
    j.at("email").get_to(u.email);
}

int main() {
    User u{42, "Ada", "ada@example.com"};
    json j = u;
    std::cout << j.dump(2) << "\\n";

    // parse
    auto parsed = json::parse(R"({"id":1,"name":"x","email":"x@x"})");
    User back = parsed.get<User>();
}""",
},
{
    "request": "C++ HTTP client with cpp-httplib",
    "language": "cpp", "framework": "cpp",
    "code": """// header-only: include <httplib.h>

#include <httplib.h>
#include <iostream>

int main() {
    httplib::Client cli("https://api.github.com");
    cli.set_default_headers({{"User-Agent", "my-cpp-app"}});

    if (auto res = cli.Get("/users/torvalds")) {
        if (res->status == 200) {
            std::cout << res->body.substr(0, 200) << "\\n";
        } else {
            std::cerr << "status: " << res->status << "\\n";
        }
    } else {
        std::cerr << "transport error: " << httplib::to_string(res.error()) << "\\n";
    }
}""",
},
{
    "request": "C++ HTTP server with cpp-httplib",
    "language": "cpp", "framework": "cpp",
    "code": """#include <httplib.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

int main() {
    httplib::Server svr;

    svr.Get("/health", [](const httplib::Request&, httplib::Response& res) {
        res.set_content(json{{"ok", true}}.dump(), "application/json");
    });

    svr.Post("/echo", [](const httplib::Request& req, httplib::Response& res) {
        try {
            auto j = json::parse(req.body);
            res.set_content(j.dump(), "application/json");
        } catch (const std::exception& e) {
            res.status = 400;
            res.set_content(std::string("bad json: ") + e.what(), "text/plain");
        }
    });

    svr.listen("0.0.0.0", 8080);
}""",
},
{
    "request": "C++ Google Test simple test",
    "language": "cpp", "framework": "cpp",
    "code": """// CMake (with FetchContent):
//   include(FetchContent)
//   FetchContent_Declare(googletest GIT_REPOSITORY https://github.com/google/googletest.git GIT_TAG v1.14.0)
//   FetchContent_MakeAvailable(googletest)
//   enable_testing()
//   add_executable(tests tests/calculator_test.cpp)
//   target_link_libraries(tests PRIVATE GTest::gtest_main)
//   include(GoogleTest)
//   gtest_discover_tests(tests)

#include <gtest/gtest.h>

int add(int a, int b) { return a + b; }

TEST(CalculatorTest, AddsPositive) {
    EXPECT_EQ(add(2, 3), 5);
}

TEST(CalculatorTest, AddsNegative) {
    EXPECT_EQ(add(-2, -3), -5);
}

class FixtureTest : public ::testing::Test {
protected:
    void SetUp() override   { /* per-test init */ }
    void TearDown() override{ /* cleanup */ }
};

TEST_F(FixtureTest, UsesFixtureState) {
    SUCCEED();
}""",
},
{
    "request": "C++ std::variant and std::visit",
    "language": "cpp", "framework": "cpp",
    "code": """#include <variant>
#include <iostream>
#include <string>

using Token = std::variant<int, double, std::string>;

void describe(const Token& t) {
    std::visit([](auto&& v) {
        using T = std::decay_t<decltype(v)>;
        if constexpr (std::is_same_v<T, int>)
            std::cout << "int " << v << "\\n";
        else if constexpr (std::is_same_v<T, double>)
            std::cout << "double " << v << "\\n";
        else
            std::cout << "string \\"" << v << "\\"\\n";
    }, t);
}

int main() {
    describe(42);
    describe(3.14);
    describe(std::string{"hi"});
}""",
},
{
    "request": "C++ std::optional usage",
    "language": "cpp", "framework": "cpp",
    "code": """#include <optional>
#include <string>
#include <iostream>

std::optional<int> safe_div(int a, int b) {
    if (b == 0) return std::nullopt;
    return a / b;
}

int main() {
    auto a = safe_div(10, 3);
    auto b = safe_div(10, 0);

    if (a) std::cout << "a = " << *a << "\\n";

    std::cout << "b = " << b.value_or(-1) << "\\n";

    // and_then / transform (C++23) for monadic-style chains
    // auto y = a.transform([](int x){ return x*2; });
}""",
},
{
    "request": "C++ ranges and views (C++20)",
    "language": "cpp", "framework": "cpp",
    "code": """#include <ranges>
#include <vector>
#include <iostream>

int main() {
    std::vector<int> v{1,2,3,4,5,6,7,8,9,10};

    // even, squared, take first 3 — lazy: nothing computed until iterated.
    auto pipeline = v
        | std::views::filter([](int n){ return n % 2 == 0; })
        | std::views::transform([](int n){ return n * n; })
        | std::views::take(3);

    for (int x : pipeline) std::cout << x << " ";   // 4 16 36
    std::cout << "\\n";
}""",
},
]
