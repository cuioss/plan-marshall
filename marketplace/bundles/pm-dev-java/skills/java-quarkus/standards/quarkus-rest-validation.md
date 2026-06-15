# Quarkus Inbound REST Validation

Inbound Bean Validation for Quarkus REST resources. Every value a resource reads from the request — body, query, path, or header — is untrusted; validate it at the resource boundary before use.

## Required Dependency

Bean Validation on REST resources is provided by `quarkus-hibernate-validator`:

```xml
<dependency>
    <groupId>io.quarkus</groupId>
    <artifactId>quarkus-hibernate-validator</artifactId>
</dependency>
```

Quarkus auto-applies the constraints below on JAX-RS resource methods once this extension is present — no manual `Validator` wiring is required for the resource layer.

## Validating Request Bodies

Annotate the body parameter with `jakarta.validation.@Valid` and put `jakarta.validation.constraints` annotations on the DTO fields. `@Valid` triggers cascading validation of the bean:

```java
import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;

public record CreateUserRequest(
        @NotBlank @Size(max = 100) String name,
        @Email String email) {
}

@Path("/users")
public class UserResource {

    @POST
    public Response create(@Valid CreateUserRequest request) {
        // request is guaranteed to satisfy every constraint here
        return Response.status(201).build();
    }
}
```

## Validating Query, Path, and Header Parameters

Apply the same `jakarta.validation.constraints` annotations directly to `@QueryParam`, `@PathParam`, and `@HeaderParam` parameters:

```java
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.HeaderParam;
import jakarta.ws.rs.PathParam;
import jakarta.ws.rs.QueryParam;

@GET
@Path("/orders/{id}")
public Response get(
        @PathParam("id") @Pattern(regexp = "[0-9]+") String id,
        @QueryParam("limit") @Min(1) int limit,
        @HeaderParam("X-Tenant") @NotNull String tenant) {
    // every inbound parameter is validated at the boundary
    return Response.ok().build();
}
```

**Normative rule:** validate every inbound REST parameter at the resource boundary. Common constraints — `@NotNull`, `@NotBlank`, `@Size`, `@Pattern`, `@Min`, `@Max`, `@Email` — cover the typical cases; `@Valid` cascades into nested beans.

## Constraint-Violation → HTTP 400 Mapping

When a constraint fails, Bean Validation raises `jakarta.validation.ConstraintViolationException`. Quarkus maps it to an **HTTP 400 Bad Request** response by default (with a structured violation payload), so a resource method never needs to catch it for the standard rejection path. Add a custom `ExceptionMapper<ConstraintViolationException>` only when the default body shape must change.

## Adversarial REST Tests

Drive negative-path requests with boundary and malformed inputs and assert the resource rejects them with HTTP 400. Reuse the existing REST Assured setup documented in `standards/quarkus-testing.md` § "REST Assured Patterns" — do not duplicate its configuration here:

```java
@QuarkusTest
class UserResourceValidationTest {

    @Test
    void rejectsBlankName() {
        given()
            .contentType("application/json")
            .body("""
                {"name": "", "email": "a@b.com"}
                """)
        .when()
            .post("/users")
        .then()
            .statusCode(400);  // @NotBlank violation -> 400
    }

    @Test
    void rejectsMalformedPathId() {
        given()
        .when()
            .get("/orders/not-a-number")
        .then()
            .statusCode(400);  // @Pattern violation -> 400
    }
}
```

Cover each constraint with at least one boundary/malformed case (empty, over-length, wrong-format, out-of-range) so the inbound validation is exercised, not just declared.
