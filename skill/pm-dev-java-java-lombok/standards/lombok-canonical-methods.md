# Lombok Canonical Methods

Standards for `@EqualsAndHashCode`, `@ToString`, `@Getter`, and `@Setter` on regular classes. When records or `@Value` are not applicable (JPA entities, mutable beans, classes with inheritance), use these annotations for `equals`, `hashCode`, and `toString`.

## @EqualsAndHashCode

```java
// Entity with business key — exclude surrogate ID
@Entity
@EqualsAndHashCode(of = "email")
public class UserEntity {
    @Id @GeneratedValue
    private Long id;
    private String email;
    private String displayName;
}

// Inheritance — use callSuper to include parent fields
@EqualsAndHashCode(callSuper = true)
public class AdminUser extends UserEntity {
    private Set<String> permissions;
}
```

**Rules**:
- **Always specify `of`** (include-list) for entities — never use the surrogate ID
- Use `callSuper = true` when the superclass has meaningful fields
- Default (all non-static, non-transient fields) is fine for simple DTOs

## @ToString

```java
// Exclude sensitive fields
@ToString(exclude = "passwordHash")
public class UserCredentials {
    private String username;
    private String passwordHash;
    private Instant lastLogin;
}

// Include only specific fields for readability
@ToString(of = {"orderId", "status"})
public class OrderEntity {
    private Long id;
    private String orderId;
    private OrderStatus status;
    private List<OrderItem> items;
}

// Inheritance
@ToString(callSuper = true)
public class PremiumOrder extends OrderEntity {
    private BigDecimal discount;
}
```

**Rules**:
- **Always exclude** sensitive data (passwords, tokens, PII)
- Use `of` for classes with many fields to keep output readable
- Use `callSuper = true` with inheritance

## @Getter / @Setter for Mutable Beans

```java
// JPA entity — minimal Lombok, explicit canonical methods
@Entity
@Getter
@Setter
@EqualsAndHashCode(of = "email")
@ToString(exclude = "passwordHash")
public class UserEntity {
    @Id @GeneratedValue
    private Long id;
    private String email;
    private String displayName;
    private String passwordHash;
}
```

**Prefer records** for immutable data. Use `@Getter`/`@Setter` + explicit `@EqualsAndHashCode`/`@ToString` only when mutability or JPA proxy requirements prevent using records.

## Common Pitfalls

| Pitfall | Wrong | Correct |
|---------|-------|---------|
| Using @Value | `@Value` for immutable objects | Use records |
| Overusing @Data | `@Data` for immutable objects | Use records |
| @Builder.Default on records | `@Builder.Default` on record component | Partial manual builder class with defaults |
| Inheritance | `extends BaseClass` | `@Delegate` with composition |
| Missing `of` on entity | `@EqualsAndHashCode` without `of` on JPA entity | `@EqualsAndHashCode(of = "businessKey")` |
| Leaking secrets | `@ToString` without exclusions | `@ToString(exclude = "password")` |
